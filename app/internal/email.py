import os
from typing import List, Optional

from fastapi import BackgroundTasks, UploadFile
from fastapi_mail import FastMail, MessageSchema
from pydantic import EmailStr
from pydantic.errors import EmailError
from sqlalchemy.orm.session import Session

from app.config import (
    CALENDAR_HOME_PAGE,
    CALENDAR_REGISTRATION_PAGE,
    CALENDAR_SITE_NAME,
    DOMAIN,
    email_conf,
)
from app.database.models import Event, User, UserEvent
from app.dependencies import templates
from app.internal.security.schema import ForgotPassword
from app.internal.utils import get_current_user

mail = FastMail(email_conf)


def send(
    session: Session,
    event_used: int,
    user_to_send: int,
    title: str,
    content: str = "",
    background_tasks: BackgroundTasks = BackgroundTasks,
) -> bool:
    """This function is being used to send emails in the background.
    It takes an event and a user and it sends the event to the user.

    Args:
        session(Session): The session to redirect to the database.
        title (str): Title of the email that is being sent.
        event_used (int): Id number of the event that is used.
        user_to_send (int): Id number of user that we want to notify.
        background_tasks (BackgroundTasks): Function from fastapi that lets
            you apply tasks in the background.

    Returns:
        bool: Returns True if the email was sent, else returns False.
    """
    event_used = session.query(Event).filter(Event.id == event_used).first()
    user_to_send = session.query(User).filter(User.id == user_to_send).first()
    if not user_to_send or not event_used:
        return False
    if not verify_email_pattern(user_to_send.email):
        return False

    subject = f"{title} {event_used.title}"
    recipients = {"email": [user_to_send.email]}.get("email")
    body = f"begins at:{event_used.start} : {event_used.content}"

    background_tasks.add_task(
        send_internal,
        subject=subject,
        recipients=recipients,
        body=body + content,
    )
    return True


def send_email_to_event_participants(
    session: Session,
    event_id: int,
    title: str,
    content: str,
) -> int:
    """This function sends emails to a mailing list of all event participants.
    it uses the function send above to do this and avoid double codes..
    Args:
        session(Session): The session to redirect to the database.
        event_id (int): Id number of the event that is used.
        title (str): Title of the email that is being sent.
        content (str): body of email sent.
    Returns:
        int: Returns the number of emails sent
        (number of valid emails in event's participants)
    """
    event_owner = session.query(Event.owner).filter(id == event_id).first()
    if event_owner != get_current_user(session):
        return 0
    # makes sure only event owner can send an email via this func.
    mailing_list = (
        session.query(User.id, User.email)
        .join(UserEvent, User.id == UserEvent.user_id)
        .filter(event_id == event_id)
        .all()
    )
    valid_mailing_list = list(filter(verify_email_pattern, mailing_list.email))
    if not valid_mailing_list:
        return 0
    # making sure app doesn't crash if emails are invalid

    event = session.query(Event).get(event_id)
    subject = f"{event.title}: {title}"
    for r in valid_mailing_list:
        send(session, event, r.id, subject, content)
    # sends the send email function parameters to send on the mailing list
    return len(valid_mailing_list)


def send_email_invitation(
    sender_name: str,
    recipient_name: str,
    recipient_mail: str,
    background_tasks: BackgroundTasks = BackgroundTasks,
) -> bool:
    """
    This function takes as parameters the sender's name,
    the recipient's name and his email address, configuration, and
    sends the recipient an invitation to his email address in
    the format HTML.
    :param sender_name: str, the sender's name
    :param recipient_name: str, the recipient's name
    :param recipient_mail: str, the recipient's email address
    :param background_tasks: (BackgroundTasks): Function from fastapi that lets
            you apply tasks in the background.
    :return: bool, True if the invitation was successfully
    sent to the recipient, and False if the entered
    email address is incorrect.
    """
    if not verify_email_pattern(recipient_mail):
        return False

    if not recipient_name:
        return False

    if not sender_name:
        return False

    template = templates.get_template("invite_mail.html")
    html = template.render(
        recipient=recipient_name,
        sender=sender_name,
        site_name=CALENDAR_SITE_NAME,
        registration_link=CALENDAR_REGISTRATION_PAGE,
        home_link=CALENDAR_HOME_PAGE,
        addr_to=recipient_mail,
    )

    subject = "Invitation"
    recipients = [recipient_mail]
    body = html
    subtype = "html"

    background_tasks.add_task(
        send_internal,
        subject=subject,
        recipients=recipients,
        body=body,
        subtype=subtype,
    )
    return True


def send_email_file(
    file_path: str,
    recipient_mail: str,
    background_tasks: BackgroundTasks = BackgroundTasks,
):
    """
    his function takes as parameters the file's path,
    the recipient's email address, configuration, and
    sends the recipient an file to his email address.
    :param file_path: str, the file's path
    :param recipient_mail: str, the recipient's email address
    :param background_tasks: (BackgroundTasks): Function from fastapi that lets
            you apply tasks in the background.
    :return: bool, True if the file was successfully
    sent to the recipient, and False if the entered
    email address is incorrect or file does not exist.
    """
    if not verify_email_pattern(recipient_mail):
        return False

    if not os.path.exists(file_path):
        return False

    subject = "File"
    recipients = [recipient_mail]
    body = "file"
    file_attachments = [file_path]

    background_tasks.add_task(
        send_internal,
        subject=subject,
        recipients=recipients,
        body=body,
        file_attachments=file_attachments,
    )
    return True


async def send_internal(
    subject: str,
    recipients: List[str],
    body: str,
    subtype: Optional[str] = None,
    file_attachments: Optional[List[str]] = None,
):
    if file_attachments is None:
        file_attachments = []

    message = MessageSchema(
        subject=subject,
        recipients=[EmailStr(recipient) for recipient in recipients],
        body=body,
        subtype=subtype,
        attachments=[
            UploadFile(file_attachment) for file_attachment in file_attachments
        ],
    )

    return await send_internal_internal(message)


async def send_internal_internal(msg: MessageSchema):
    """
    This function receives message and
    configuration as parameters and sends the message.
    :param msg: MessageSchema, message
    :return: None
    """
    await mail.send_message(msg)


def verify_email_pattern(email: str) -> bool:
    """
    This function checks the correctness
    of the entered email address
    :param email: str, the entered email address
    :return: bool,
    True if the entered email address is correct,
    False if the entered email address is incorrect.
    """
    try:
        EmailStr.validate(email)
        return True
    except EmailError:
        return False


async def send_reset_password_mail(
    user: ForgotPassword,
    background_tasks: BackgroundTasks,
) -> bool:
    """
    This function sends a reset password email to user.
    :param user: ForgotPassword schema.
        Contains user's email address, jwt verifying token.
    :param background_tasks: (BackgroundTasks): Function from fastapi that lets
            you apply tasks in the background.
    returns True
    """
    params = f"?email_verification_token={user.email_verification_token}"
    template = templates.get_template("reset_password_mail.html")
    html = template.render(
        recipient=user.username.lstrip("@"),
        link=f"{DOMAIN}/reset-password{params}",
        email=user.email,
    )
    background_tasks.add_task(
        send_internal,
        subject="Calendar reset password",
        recipients=[user.email],
        body=html,
        subtype="html",
    )
    return True
