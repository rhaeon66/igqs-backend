from django.core.management.base import BaseCommand

from admissions.models import AdmissionApplication
from admissions.receipts import generate_receipt_pdf


class Command(BaseCommand):
    help = (
        "Rebuild every stored receipt PDF from the current application data "
        "(e.g. after a receipt layout or font fix). No emails are sent."
    )

    def handle(self, *args, **options):
        rebuilt = failed = 0
        for application in AdmissionApplication.objects.exclude(receipt_pdf="").iterator():
            try:
                generate_receipt_pdf(application, force=True)
            except Exception as exc:
                failed += 1
                self.stderr.write(f"{application.application_id}: {exc}")
            else:
                rebuilt += 1
        self.stdout.write(self.style.SUCCESS(f"Rebuilt {rebuilt} receipt(s); {failed} failed."))
