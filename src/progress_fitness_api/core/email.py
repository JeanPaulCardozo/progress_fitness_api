import os
import resend
from pathlib import Path

from dotenv import load_dotenv
from progress_fitness_api.core.security import RESET_MINUTES

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")

RESET_TEMPLATE = (
    Path(__file__).parent / "templates" / "reset_password.html"
).read_text(encoding="utf-8")


def send_reset_email(to: str, link: str) -> None:
    if not resend.api_key:
        print(f"Enlace para restablecer la contraseña de {to}: {link}")
        return

    html = RESET_TEMPLATE.replace("{{link}}", link).replace(
        "{{minutes}}", str(RESET_MINUTES)
    )

    resend.Emails.send(
        {
            "from": os.getenv("EMAIL_FROM"),
            "to": [to],
            "subject": "Restablece tu contraseña de ProgressFit",
            "html": html,
            "text": (
                "Pediste cambiar tu contraseña de ProgressFit.\n\n"
                f"Abre este enlace para elegir una nueva: {link}\n\n"
                f"Caduca en {RESET_MINUTES} minutos y solo se puede usar una vez. "
                "Si no lo pediste, ignora este correo."
            ),
        }
    )
