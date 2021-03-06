# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""Test that computed MSIDs work as expected."""

import numpy as np
import pytest

from .. import fetch_eng, fetch_sci, fetch as fetch_cxc
from ..derived.base import DerivedParameter
from ..derived.comps import ComputedMsid

try:
    import maude
    date1 = '2016:001:00:00:00.1'
    date2 = '2016:001:00:00:02.0'
    maude.get_msids(msids='ccsdsid', start=date1, stop=date2)
except Exception:
    HAS_MAUDE = False
else:
    HAS_MAUDE = True


class Comp_Passthru(ComputedMsid):
    """Pass MSID through unchanged (for checking that stats work)"""
    msid_match = r'passthru_(\w+)'

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        dat = self.fetch_eng.MSID(msid_args[0], tstart, tstop)

        out = {'vals': dat.vals,
               'bads': dat.bads,
               'times': dat.times,
               'unit': dat.unit}
        return out


class Comp_Val_Plus_Five(ComputedMsid):
    """Silly base comp to add 5 to the value"""
    msid_match = r'comp_(\w+)_plus_five'

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        dat = self.fetch_sys.MSID(msid_args[0], tstart, tstop)

        out = {'vals': dat.vals + 5,
               'bads': dat.bads,
               'times': dat.times,
               'unit': dat.unit}
        return out


class Comp_CSS1_NPM_SUN(ComputedMsid, DerivedParameter):
    """Coarse Sun Sensor Counts 1 filtered for NPM and SA Illuminated

    Defined as CSS-1 current converted back into counts
    (AOCSSI1 * 4095 / 5.49549) when in NPM (AOPCADMD==1) and SA is illuminated
    (AOSAILLM==1).  Otherwise, "Bads" flag is set equal to one.

    """
    rootparams = ['aocssi1', 'aopcadmd', 'aosaillm']
    time_step = 1.025
    max_gap = 10.0
    msid_match = 'comp_css1_npm_sun'

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        # Get an interpolated MSIDset for rootparams
        msids = self.fetch(tstart, tstop)

        # Do the computation and set bad values
        npm_sun = ((msids['aopcadmd'].vals == 'NPNT') &
                   (msids['aosaillm'].vals == 'ILLM'))
        msids.bads = msids.bads | ~npm_sun
        css1_npm_sun = msids['aocssi1'].vals * 4095 / 5.49549

        out = {'vals': css1_npm_sun,
               'times': msids.times,
               'bads': msids.bads,
               'unit': None}
        return out


def test_comp_from_derived_parameter():
    """Test that on-the-fly comp gives same result as derived parameter from
    same code.
    """
    dat1 = fetch_eng.Msid('comp_css1_npm_sun', '2020:001', '2020:010')
    dat2 = fetch_eng.Msid('dp_css1_npm_sun', '2020:001', '2020:010')

    for attr in ('vals', 'times', 'bads', 'unit'):
        assert np.all(getattr(dat1, attr) == getattr(dat2, attr))


@pytest.mark.parametrize('fetch,unit', [(fetch_eng, 'DEGF'),
                                        (fetch_sci, 'DEGC'),
                                        (fetch_cxc, 'K')])
def test_simple_comp(fetch, unit):
    dat1 = fetch.Msid('tephin', '2020:001', '2020:010')
    dat2 = fetch.Msid('comp_tephin_plus_five', '2020:001', '2020:010')
    assert np.all(dat1.vals + 5 == dat2.vals)
    assert np.all(dat1.times == dat2.times)
    assert np.all(dat1.bads == dat2.bads)
    assert dat1.unit == dat2.unit
    assert dat2.unit == unit


@pytest.mark.skipif("not HAS_MAUDE")
@pytest.mark.parametrize('fetch,unit', [(fetch_eng, 'DEGF'),
                                        (fetch_sci, 'DEGC'),
                                        (fetch_cxc, 'K')])
def test_simple_comp_with_maude(fetch, unit):
    with fetch.data_source('maude'):
        dat1 = fetch.Msid('tephin', '2020:001', '2020:003')
        dat2 = fetch.Msid('comp_tephin_plus_five', '2020:001', '2020:003')
        assert np.all(dat1.vals + 5 == dat2.vals)
        assert np.all(dat1.times == dat2.times)
        assert np.all(dat1.bads == dat2.bads)
        assert dat1.unit == dat2.unit
        assert dat2.unit == unit


def test_mups_valve():
    colnames = ['vals', 'times', 'bads', 'vals_raw',
                'vals_nan', 'vals_corr', 'vals_model', 'source']

    # Use the chandra_models 6854df4d commit for testing. This is a commit of
    # chandra_models that has the epoch dates changes to fully-qualified values
    # like 2017:123:12:00:00 (instead of 2017:123). This allows these regression
    # tests to pass with Chandra.Time 3.x or 4.0+.
    dat = fetch_eng.MSID('PM2THV1T_clean_6854df4d', '2020:001:12:00:00', '2020:010:12:00:00')
    assert dat.unit == 'DEGF'
    assert len(dat.vals) == 36661
    ok = dat.source != 0
    # Temps are reasonable for degF
    assert np.all((dat.vals[ok] > 55) & (dat.vals[ok] < 220))
    assert np.count_nonzero(ok) == 31524
    assert dat.colnames == colnames
    for attr in colnames:
        assert len(dat.vals) == len(getattr(dat, attr))

    dat = fetch_sci.Msid('PM2THV1T_clean_6854df4d', '2020:001:12:00:00', '2020:010:12:00:00')
    assert dat.unit == 'DEGC'
    ok = dat.source != 0
    # Temps are reasonable for degC
    assert np.all((dat.vals[ok] > 10) & (dat.vals[ok] < 110))
    assert len(dat.vals) == 31524  # Some bad values
    assert dat.colnames == colnames
    for attr in colnames:
        if attr != 'bads':
            assert len(dat.vals) == len(getattr(dat, attr))

    dat = fetch_cxc.MSID('PM1THV2T_clean_6854df4d', '2020:001:12:00:00', '2020:010:12:00:00')
    ok = dat.source != 0
    # Temps are reasonable for K
    assert np.all((dat.vals[ok] > 280) & (dat.vals[ok] < 380))
    assert len(dat.vals) == 36661  # Same as PM2THV1T
    assert dat.colnames == colnames
    for attr in colnames:
        assert len(dat.vals) == len(getattr(dat, attr))

    # Check using default master branch
    dat = fetch_eng.Msid('pm1thv2t_clean', '2020:001:12:00:00', '2020:010:12:00:00')
    assert len(dat.vals) == 36240  # Some bad values
    assert len(dat.source) == 36240  # Filtering applies to sources
    assert dat.colnames == colnames
    for attr in colnames:
        if attr != 'bads':
            assert len(dat.vals) == len(getattr(dat, attr))


def test_cmd_states():
    start, stop = '2020:002:08:00:00', '2020:002:10:00:00'
    dat = fetch_eng.Msid('cmd_state_pitch_1000', start, stop)
    exp_vals = np.array([55.99128956, 55.8747053, 55.8747053, 90.66266599,
                         159.06945155, 173.11528258, 173.11528258, 173.11528258])
    assert np.allclose(dat.vals, exp_vals)
    assert type(dat.vals) is np.ndarray
    assert np.allclose(np.diff(dat.times), 1025.0)
    assert not np.any(dat.bads)
    assert dat.unit is None

    dat = fetch_eng.Msid('cmd_state_pcad_mode_1000', start, stop)
    exp_vals = np.array(['NPNT', 'NPNT', 'NPNT', 'NMAN', 'NMAN', 'NPNT', 'NPNT', 'NPNT'])
    assert np.all(dat.vals == exp_vals)
    assert type(dat.vals) is np.ndarray
    assert np.allclose(np.diff(dat.times), 1025.0)


@pytest.mark.parametrize('stat', ['5min', 'daily'])
def test_stats(stat):
    start, stop = '2020:001:12:00:00', '2020:010:12:00:00'

    dat = fetch_eng.Msid('pitch', start, stop, stat=stat)
    datc = fetch_eng.Msid('passthru_pitch', start, stop, stat=stat)

    for attr in datc.colnames:
        val = getattr(dat, attr)
        valc = getattr(datc, attr)
        if attr == 'bads':
            assert val == valc
            continue
        assert val.dtype == valc.dtype
        if val.dtype.kind == 'f':
            assert np.allclose(val, valc)
        else:
            assert np.all(val == valc)
