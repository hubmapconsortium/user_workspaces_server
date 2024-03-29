from logging import Handler


class AsyncEmailHandler(Handler):
    def __init__(self, subject, from_email, email_list):
        Handler.__init__(self)
        self.subject = subject
        self.from_email = from_email
        self.email_list = email_list

    def emit(self, record):
        from django_q.tasks import async_task

        msg = self.format(record)
        email_tuple = []

        for email in self.email_list:
            email_tuple.append((self.subject, msg, self.from_email, [email]))

        async_task("django.core.mail.send_mass_mail", tuple(email_tuple))
