import re
import dns.resolver
import smtplib
import pandas as pd
import streamlit as st
import socket
import threading
import time
from queue import Queue

# Set a global timeout for network operations
socket.setdefaulttimeout(5)

# Email formats
email_formats = [
    "{first}.{last}@{domain}",
    "{first[0]}.{last}@{domain}",
    "{first}.{last[0]}@{domain}",
    "{first[0]}.{last[0]}@{domain}",
    "{last}.{first}@{domain}",
    "{last}.{first[0]}@{domain}",
    "{first}_{last}@{domain}",
    "{first}@{domain}",
    "{last}@{domain}",
    "{first}{last}@{domain}",
    "{first[0]}{last}@{domain}",
    "{first}{last[0]}@{domain}",
]

# Free email domains to skip
free_email_domains = [
    "gmail.com", "yahoo.com", "hotmail.com", "aol.com", "live.com",
    "outlook.com", "icloud.com", "verizon.net", "protonmail.com", "zoho.com"
]

# Functions
def is_valid_email(email):
    """Check if the email has a valid syntax."""
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email)

def domain_exists(domain):
    """Check if the domain has valid MX records."""
    try:
        dns.resolver.resolve(domain, 'MX', lifetime=5)
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
        return False

def smtp_check(email):
    """Verify deliverability via SMTP on port 25."""
    domain = email.split('@')[-1]
    try:
        mx_records = dns.resolver.resolve(domain, 'MX', lifetime=5)
        mx_host = str(mx_records[0].exchange)

        with smtplib.SMTP(mx_host, 25, timeout=5) as smtp:
            smtp.helo()
            smtp.mail('test@example.com')
            code, _ = smtp.rcpt(email)
            return code == 250
    except Exception:
        return False

# Thread function
def process_emails(queue, results, progress, total, start_time, progress_text):
    while not queue.empty():
        first, last, domain = queue.get()

        if domain.lower() in free_email_domains:
            results.append({
                "First Name": first,
                "Last Name": last,
                "Email": f"{first.lower()}.{last.lower()}@{domain.lower()}",
                "Status": "Skipped (Free Email Domain)"
            })
            queue.task_done()
            continue

        if not domain_exists(domain):
            results.append({
                "First Name": first,
                "Last Name": last,
                "Email": f"{domain}",
                "Status": "Invalid"
            })
            queue.task_done()
            continue

        for format_ in email_formats:
            email = format_.format(
                first=first.lower(),
                last=last.lower(),
                domain=domain.lower()
            )
            if is_valid_email(email) and smtp_check(email):
                results.append({
                    "First Name": first,
                    "Last Name": last,
                    "Email": email,
                    "Status": "Valid"
                })
                break
        else:
            results.append({
                "First Name": first,
                "Last Name": last,
                "Email": f"{domain}",
                "Status": "Invalid"
            })

        queue.task_done()
        progress[0] += 1
        elapsed_time = time.time() - start_time
        progress_text.text(f"Processed: {progress[0]}/{total} | Elapsed Time: {elapsed_time:.2f} sec")

# Main function
def generate_and_verify_emails(names_domains, num_threads=5):
    queue = Queue()
    results =
    progress = [0]
    total = len(names_domains)
    start_time = time.time()

    for _, row in names_domains.iterrows():
        queue.put((row['First Name'], row['Last Name'], row['Domain']))

    progress_text = st.empty()  # Create an empty container for live updates

    threads =
    for _ in range(num_threads):
        thread = threading.Thread(target=process_emails, args=(queue, results, progress, total, start_time, progress_text))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    total_time = time.time() - start_time
    return results, total_time

# Streamlit UI
st.title("Email Verification Tool")
st.markdown("**Please upload a CSV file with the following format:**")
st.markdown("**First Name in Column A, Last Name in Column B, and Domain in Column C.**")
st.write("Ensure the column names match exactly: 'First Name', 'Last Name', and 'Domain'.")

uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])

if uploaded_file is not None:
    names_domains = pd.read_csv(uploaded_file)

    if {'First Name', 'Last Name', 'Domain'}.issubset(names_domains.columns):
        st.write("Processing emails...")

        results, total_time = generate_and_verify_emails(names_domains)

        df = pd.DataFrame(results)
        st.write(df)

        # Show total time taken in minutes
        total_time_minutes = total_time / 60
        st.write(f"Total time taken: {total_time_minutes:.2f} minutes")

        # Download results
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Results", csv, "email_validation_results.csv", "text/csv")

        # Copy results
        results_text = df.to_csv(index=False, sep='\t')
        st.text_area("Copy Results", results_text, height=200)
    else:
        st.error("CSV file must contain 'First Name', 'Last Name', and 'Domain' columns.")
