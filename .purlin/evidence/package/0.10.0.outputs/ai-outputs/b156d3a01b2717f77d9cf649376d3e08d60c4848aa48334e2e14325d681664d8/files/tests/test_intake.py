import pytest

from src.intake import Bench, IntakeError, at

T0 = at('2026-03-01T08:00')
T1 = at('2026-03-01T10:00')


# purlin: sample_intake PROOF-1
def test_an_empty_barcode_is_refused():
    with pytest.raises(IntakeError) as refused:
        Bench().intake('', 'BOS', T0, T1)
    assert str(refused.value) == 'barcode is required'


# purlin: sample_intake PROOF-2
def test_a_barcode_of_spaces_is_refused():
    with pytest.raises(IntakeError) as refused:
        Bench().intake('   ', 'BOS', T0, T1)
    assert str(refused.value) == 'barcode is required'


# purlin: sample_intake PROOF-3
def test_eight_digits_are_accepted():
    record = Bench().intake('LC-12345678', 'BOS', T0, T1)
    assert record['status'] == 'accepted'


# purlin: sample_intake PROOF-4
def test_seven_digits_are_refused():
    with pytest.raises(IntakeError) as refused:
        Bench().intake('LC-1234567', 'BOS', T0, T1)
    assert str(refused.value) == 'barcode LC-1234567 is not LC- and 8 digits'


# purlin: sample_intake PROOF-5
def test_age_is_whole_hours():
    collected = at('2026-03-01T08:00')
    received = at('2026-03-02T09:30')
    record = Bench().intake('LC-12345678', 'BOS', collected, received)
    assert record['age_hours'] == 25


# purlin: sample_intake PROOF-6
def test_73_hours_is_expired():
    record = Bench().intake('LC-12345678', 'BOS', at('2026-03-01T08:00'),
                            at('2026-03-04T09:00'))
    assert record['status'] == 'expired'


# purlin: sample_intake PROOF-7
def test_72_hours_is_accepted():
    record = Bench().intake('LC-12345678', 'BOS', at('2026-03-01T08:00'),
                            at('2026-03-04T07:00'))
    assert record['status'] == 'accepted'


# purlin: sample_intake PROOF-8
def test_a_warm_frozen_sample_is_an_excursion():
    record = Bench().intake('LC-12345678', 'BOS', T0, T1, storage='frozen',
                            temperature_c=-19.9)
    assert record['status'] == 'temperature excursion'


# purlin: sample_intake PROOF-9
def test_a_frozen_sample_at_minus_20_is_accepted():
    record = Bench().intake('LC-12345678', 'BOS', T0, T1, storage='frozen',
                            temperature_c=-20.0)
    assert record['status'] == 'accepted'


# purlin: sample_intake PROOF-10
def test_received_before_collected_is_refused():
    with pytest.raises(IntakeError) as refused:
        Bench().intake('LC-12345678', 'BOS', at('2026-03-02T08:00'),
                       at('2026-03-01T08:00'))
    assert str(refused.value) == 'received before collected'


# purlin: sample_intake PROOF-11
def test_accession_numbers_count_up():
    bench = Bench()
    first = bench.intake('LC-00000001', 'BOS', T0, T1)
    second = bench.intake('LC-00000002', 'BOS', T0, T1)
    print(first['accession'], second['accession'])


# purlin: sample_intake PROOF-12
def test_a_barcode_received_twice_is_refused():
    bench = Bench()
    bench.intake('LC-12345678', 'BOS', T0, T1)
    with pytest.raises(IntakeError) as refused:
        bench.intake('LC-12345678', 'BOS', T0, T1)
    assert str(refused.value) == 'barcode LC-12345678 was already received'
