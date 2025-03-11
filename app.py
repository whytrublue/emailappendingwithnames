import re
import dns.resolver
import smtplib
import pandas as pd
import streamlit as st
import socket
import threading
import time
from queue import Queue

# ... (rest of the functions: is_valid_email, domain_exists, smtp_check, process_emails) ...

# Main function
def generate_and_verify_emails(names_domains, num_threads=5):
    queue = Queue()
    results = []
    progress = [0]
    total = len(names_domains)
    start_time = time.time()

    for _, row in names_domains.iterrows():
        queue.put((row['First Name'], row['Last Name'], row['Domain']))

    progress_text = st.empty()  # Create an empty container for live updates

    threads = []
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

        # Initialize an empty container for the timer
        timer_placeholder = st.empty()
        start_time = time.time()

        def update_timer():
            while True:
                elapsed_time = time.time() - start_time
                timer_placeholder.text(f"Elapsed Time: {elapsed_time:.2f} sec")
                if 'results' in locals() and len(results) == len(names_domains):
                    break
                time.sleep(0.1)

        timer_thread = threading.Thread(target=update_timer)
        timer_thread.start()

        results, total_time = generate_and_verify_emails(names_domains)

        timer_thread.join() # wait for the timer thread to finish.

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
