"""Sample intake for a clinical lab: what is accepted at the receiving bench."""
import re
from datetime import datetime

BARCODE = re.compile(r'^LC-\d{8}$')
MAX_AGE_HOURS = 72
FROZEN_MAX_C = -20.0


class IntakeError(Exception):
    """A sample that cannot be received at all."""


def age_hours(collected, received):
    """Whole hours between collection and receipt, rounded down."""
    seconds = (received - collected).total_seconds()
    return int(seconds // 3600)


class Bench:
    """One receiving bench: what it has received, and each site's sequence."""

    def __init__(self):
        self.received = {}
        self.sequence = {}

    def intake(self, barcode, site, collected, received, storage='ambient',
               temperature_c=None):
        """Receive one sample; the record it is stored as."""
        if barcode is None or not barcode.strip():
            raise IntakeError('barcode is required')
        if not BARCODE.match(barcode):
            raise IntakeError('barcode %s is not LC- and 8 digits' % barcode)
        if barcode in self.received:
            raise IntakeError('barcode %s was already received' % barcode)
        if received < collected:
            raise IntakeError('received before collected')
        age = age_hours(collected, received)
        status = 'accepted'
        if age > MAX_AGE_HOURS:
            status = 'expired'
        elif storage == 'frozen' and temperature_c is not None \
                and temperature_c > FROZEN_MAX_C:
            status = 'temperature excursion'
        accession = None
        if status == 'accepted':
            number = self.sequence.get(site, 0) + 1
            self.sequence[site] = number
            accession = '%s-%d-%05d' % (site, received.year, number)
        record = {'barcode': barcode, 'site': site, 'age_hours': age,
                  'status': status, 'accession': accession}
        self.received[barcode] = record
        return record


def at(text):
    """A time written `2026-03-01T08:00`."""
    return datetime.strptime(text, '%Y-%m-%dT%H:%M')
