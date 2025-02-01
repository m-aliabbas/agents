import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(to_email, subject, body):
    email_address = 'maliabbas366@gmail.com'  # Your email address
    email_password = 'cgcn zilt rqkd nkcy'  # Your app password

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = email_address
    msg['To'] = to_email
    msg['Subject'] = subject

    # HTML Email Template
    html_template = f"""
    <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: auto;
                    background: #ffffff;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0px 0px 10px #cccccc;
                }}
                h2 {{
                    color: #333;
                    text-align: center;
                }}
                p {{
                    font-size: 16px;
                    line-height: 1.5;
                    color: #555;
                }}
                .footer {{
                    text-align: center;
                    font-size: 14px;
                    color: #888;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>{subject}</h2>
                <p>{body}</p>
                <div class="footer">
                    <p>Best Regards,<br> Cognitex Bot</p>
                </div>
            </div>
        </body>
    </html>
    """

    # Attach the HTML content to the email
    msg.attach(MIMEText(html_template, 'html'))

    try:
        # Set up the server and start TLS encryption
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()

        # Login to the email server
        server.login(email_address, email_password)

        # Send the email
        server.sendmail(email_address, to_email, msg.as_string())

        # Close the connection
        server.quit()

        # print("Email sent successfully!")
        return "Callback scheduled successfully!"
    except Exception as e:
        return "Something went wrong while sending the email for callback. Please try again later."


if __name__ == "__main__":
    # Example of how to use the function
    recipient_email = ''
    email_subject = 'Test Email from Function'
    email_body = 'This is a test email sent using a function.'

    # Call the function to send the email
    send_email(recipient_email, email_subject, email_body)
