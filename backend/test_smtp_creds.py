import smtplib
from email.mime.text import MIMEText

def test_smtp(username, password):
    try:
        print(f"Testing with password: {password}")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(username, password)
        server.quit()
        print("LOGIN SUCCESSFUL!")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"Authentication Error: {e}")
        return False
    except Exception as e:
        print(f"Other Error: {e}")
        return False

user = "yanpallewarsampada@gmail.com"
test_smtp(user, "your-icgvtpnzassciyep")
test_smtp(user, "icgvtpnzassciyep")
