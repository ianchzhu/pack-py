import smtplib
import threading
import imaplib
from email.mime.text import MIMEText
from email.header import Header
def send(to, subject, message, me):
    if "," in to:
        to = to.split(",")
    else:
        to = [to]
    
    m = MIMEText(message)
    m['Subject'] = Header(subject, 'utf-8')
    m['From'] = me
    m['To'] = ",".join(to)
    print("[INFO] mail created]")
    try:
        smtpobj = smtplib.SMTP_SSL(host="s1.maildns.net", port=465)
        print("[INFO] connected to server]")
        smtpobj.set_debuglevel(0)
        smtpobj.login("qtbmuakm","my8sB3TL0@.L3e")
        print("[INFO] logged in]")
        # Fixed: Added the missing message parameter
        smtpobj.sendmail(me, to, m.as_string())
        print("[INFO] mail sent]")
        smtpobj.quit()  # Added proper connection cleanup
        return "Email sent successfully"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

def getinbox(emailaddress):
    try:
        mail = imaplib.IMAP4_SSL("s1.maildns.net", 993)
        mail.debug = 1
        mail.login("qtbmuakm", "my8sB3TL0@.L3e")
        mail.select("INBOX")
        result, data = mail.search(None, "ALL")
        message_ids = data[0].split()
        print(message_ids)
        emails = []
        # Process the most recent 10 emails
        for msg_id in message_ids[-10:]:
            result, msg_data = mail.fetch(msg_id, "(RFC822)")
            if result == "OK":
                import email
                email_message = email.message_from_bytes(msg_data[0][1])
                
                # Extract email details
                subject = email_message.get("Subject", "No Subject")
                from_addr = email_message.get("From", "Unknown Sender")
                date = email_message.get("Date", "Unknown Date")
                
                # Get message body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                emails.append({
                    "from": from_addr,
                    "subject": subject,
                    "date": date,
                    "message": body
                })
        
        mail.logout()
        return emails
        
    except Exception as e:
        print(f"Error retrieving inbox: {str(e)}")
        return []