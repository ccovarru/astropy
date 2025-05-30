# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Separate tests specifically for equivalencies."""

import numpy as np

# THIRD-PARTY
import pytest
from numpy.testing import assert_allclose

# LOCAL
from astropy import constants
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from astropy.units.equivalencies import Equivalency
from astropy.utils.exceptions import AstropyDeprecationWarning


def test_find_equivalent_units():
    # Only finds units in the namespace
    e1 = (u.m**3).find_equivalent_units()
    assert len(e1) == 1
    assert e1[0] == u.l
    # Regression test for gh-16124
    e2 = (u.m**-3).find_equivalent_units()
    assert len(e2) == 0


def test_dimensionless_angles():
    # test that the angles_dimensionless option allows one to change
    # by any order in radian in the unit (#1161)
    rad1 = u.dimensionless_angles()
    assert u.radian.to(1, equivalencies=rad1) == 1.0
    assert u.deg.to(1, equivalencies=rad1) == u.deg.to(u.rad)
    assert u.steradian.to(1, equivalencies=rad1) == 1.0
    assert u.dimensionless_unscaled.to(u.steradian, equivalencies=rad1) == 1.0
    # now quantities
    assert (1.0 * u.radian).to_value(1, equivalencies=rad1) == 1.0
    assert (1.0 * u.deg).to_value(1, equivalencies=rad1) == u.deg.to(u.rad)
    assert (1.0 * u.steradian).to_value(1, equivalencies=rad1) == 1.0
    # more complicated example
    I = 1.0e45 * u.g * u.cm**2
    Omega = u.cycle / (1.0 * u.s)
    Erot = 0.5 * I * Omega**2
    # check that equivalency makes this work
    Erot_in_erg1 = Erot.to(u.erg, equivalencies=rad1)
    # and check that value is correct
    assert_allclose(Erot_in_erg1.value, (Erot / u.radian**2).to_value(u.erg))

    # test built-in equivalency in subclass
    class MyRad1(u.Quantity):
        _equivalencies = rad1

    phase = MyRad1(1.0, u.cycle)
    assert phase.to_value(1) == u.cycle.to(u.radian)


@pytest.mark.parametrize("log_unit", (u.mag, u.dex, u.dB))
def test_logarithmic(log_unit):
    # check conversion of mag, dB, and dex to dimensionless and vice versa
    with pytest.raises(u.UnitsError):
        log_unit.to(1, 0.0)
    with pytest.raises(u.UnitsError):
        u.dimensionless_unscaled.to(log_unit)

    assert log_unit.to(1, 0.0, equivalencies=u.logarithmic()) == 1.0
    assert u.dimensionless_unscaled.to(log_unit, equivalencies=u.logarithmic()) == 0.0
    # also try with quantities

    q_dex = np.array([0.0, -1.0, 1.0, 2.0]) * u.dex
    q_expected = 10.0**q_dex.value * u.dimensionless_unscaled
    q_log_unit = q_dex.to(log_unit)
    assert np.all(q_log_unit.to(1, equivalencies=u.logarithmic()) == q_expected)
    assert np.all(q_expected.to(log_unit, equivalencies=u.logarithmic()) == q_log_unit)
    with u.set_enabled_equivalencies(u.logarithmic()):
        assert np.all(np.abs(q_log_unit - q_expected.to(log_unit)) < 1.0e-10 * log_unit)


doppler_functions = [u.doppler_optical, u.doppler_radio, u.doppler_relativistic]


@pytest.mark.parametrize("function", doppler_functions)
def test_doppler_frequency_0(function):
    rest = 105.01 * u.GHz
    velo0 = rest.to(u.km / u.s, equivalencies=function(rest))
    assert velo0.value == 0


@pytest.mark.parametrize("function", doppler_functions)
def test_doppler_wavelength_0(function):
    rest = 105.01 * u.GHz
    q1 = 0.00285489437196 * u.m
    velo0 = q1.to(u.km / u.s, equivalencies=function(rest))
    np.testing.assert_almost_equal(velo0.value, 0, decimal=6)


@pytest.mark.parametrize("function", doppler_functions)
def test_doppler_energy_0(function):
    rest = 105.01 * u.GHz
    q1 = 0.0004342864648539744 * u.eV
    velo0 = q1.to(u.km / u.s, equivalencies=function(rest))
    np.testing.assert_almost_equal(velo0.value, 0, decimal=6)


@pytest.mark.parametrize("function", doppler_functions)
def test_doppler_frequency_circle(function):
    rest = 105.01 * u.GHz
    shifted = 105.03 * u.GHz
    velo = shifted.to(u.km / u.s, equivalencies=function(rest))
    freq = velo.to(u.GHz, equivalencies=function(rest))
    np.testing.assert_almost_equal(freq.value, shifted.value, decimal=7)


@pytest.mark.parametrize("function", doppler_functions)
def test_doppler_wavelength_circle(function):
    rest = 105.01 * u.nm
    shifted = 105.03 * u.nm
    velo = shifted.to(u.km / u.s, equivalencies=function(rest))
    wav = velo.to(u.nm, equivalencies=function(rest))
    np.testing.assert_almost_equal(wav.value, shifted.value, decimal=7)


@pytest.mark.parametrize("function", doppler_functions)
def test_doppler_energy_circle(function):
    rest = 1.0501 * u.eV
    shifted = 1.0503 * u.eV
    velo = shifted.to(u.km / u.s, equivalencies=function(rest))
    en = velo.to(u.eV, equivalencies=function(rest))
    np.testing.assert_almost_equal(en.value, shifted.value, decimal=7)


values_ghz = (999.899940784289, 999.8999307714406, 999.8999357778647)


@pytest.mark.parametrize(
    ("function", "value"), list(zip(doppler_functions, values_ghz))
)
def test_30kms(function, value):
    rest = 1000 * u.GHz
    velo = 30 * u.km / u.s
    shifted = velo.to(u.GHz, equivalencies=function(rest))
    np.testing.assert_almost_equal(shifted.value, value, decimal=7)


bad_values = (5, 5 * u.Jy, None)


@pytest.mark.parametrize(
    ("function", "value"), list(zip(doppler_functions, bad_values))
)
def test_bad_restfreqs(function, value):
    with pytest.raises(u.UnitsError):
        function(value)


@pytest.mark.parametrize(
    ("z", "rv_ans"),
    [
        (0, 0 * (u.km / u.s)),
        (0.001, 299642.56184583 * (u.m / u.s)),
        (-1, -2.99792458e8 * (u.m / u.s)),
    ],
)
def test_doppler_redshift(z, rv_ans):
    z_in = z * u.dimensionless_unscaled
    rv_out = z_in.to(u.km / u.s, u.doppler_redshift())
    z_out = rv_out.to(u.dimensionless_unscaled, u.doppler_redshift())
    assert_quantity_allclose(rv_out, rv_ans)
    assert_quantity_allclose(z_out, z_in)  # Check roundtrip


def test_doppler_redshift_no_cosmology():
    from astropy.cosmology.units import redshift

    with pytest.raises(u.UnitConversionError, match="not convertible"):
        (0 * (u.km / u.s)).to(redshift, u.doppler_redshift())


def test_massenergy():
    # The relative tolerance of these tests is set by the uncertainties
    # in the charge of the electron, which is known to about
    # 3e-9 (relative tolerance).  Therefore, we limit the
    # precision of the tests to 1e-7 to be safe.  The masses are
    # (loosely) known to ~ 5e-8 rel tolerance, so we couldn't test to
    # 1e-7 if we used the values from astropy.constants; that is,
    # they might change by more than 1e-7 in some future update, so instead
    # they are hardwired here.

    # Electron, proton, neutron, muon, 1g
    mass_eV = u.Quantity(
        [510.998928e3, 938.272046e6, 939.565378e6, 105.6583715e6, 5.60958884539e32],
        u.eV,
    )
    mass_g = u.Quantity(
        [9.10938291e-28, 1.672621777e-24, 1.674927351e-24, 1.88353147e-25, 1], u.g
    )
    # Test both ways
    assert np.allclose(
        mass_eV.to_value(u.g, equivalencies=u.mass_energy()), mass_g.value, rtol=1e-7
    )
    assert np.allclose(
        mass_g.to_value(u.eV, equivalencies=u.mass_energy()), mass_eV.value, rtol=1e-7
    )

    # Basic tests of 'derived' equivalencies
    # Surface density
    sdens_eV = u.Quantity(5.60958884539e32, u.eV / u.m**2)
    sdens_g = u.Quantity(1e-4, u.g / u.cm**2)
    assert np.allclose(
        sdens_eV.to_value(u.g / u.cm**2, equivalencies=u.mass_energy()),
        sdens_g.value,
        rtol=1e-7,
    )
    assert np.allclose(
        sdens_g.to_value(u.eV / u.m**2, equivalencies=u.mass_energy()),
        sdens_eV.value,
        rtol=1e-7,
    )

    # Density
    dens_eV = u.Quantity(5.60958884539e32, u.eV / u.m**3)
    dens_g = u.Quantity(1e-6, u.g / u.cm**3)
    assert np.allclose(
        dens_eV.to_value(u.g / u.cm**3, equivalencies=u.mass_energy()),
        dens_g.value,
        rtol=1e-7,
    )
    assert np.allclose(
        dens_g.to_value(u.eV / u.m**3, equivalencies=u.mass_energy()),
        dens_eV.value,
        rtol=1e-7,
    )

    # Power
    pow_eV = u.Quantity(5.60958884539e32, u.eV / u.s)
    pow_g = u.Quantity(1, u.g / u.s)
    assert np.allclose(
        pow_eV.to_value(u.g / u.s, equivalencies=u.mass_energy()),
        pow_g.value,
        rtol=1e-7,
    )
    assert np.allclose(
        pow_g.to_value(u.eV / u.s, equivalencies=u.mass_energy()),
        pow_eV.value,
        rtol=1e-7,
    )


def test_is_equivalent():
    assert u.m.is_equivalent(u.pc)
    assert u.cycle.is_equivalent(u.mas)
    assert not u.cycle.is_equivalent(u.dimensionless_unscaled)
    assert u.cycle.is_equivalent(u.dimensionless_unscaled, u.dimensionless_angles())
    assert not (u.Hz.is_equivalent(u.J))
    assert u.Hz.is_equivalent(u.J, u.spectral())
    assert u.J.is_equivalent(u.Hz, u.spectral())
    assert u.pc.is_equivalent(u.arcsecond, u.parallax())
    assert u.arcminute.is_equivalent(u.au, u.parallax())

    # Pass a tuple for multiple possibilities
    assert u.cm.is_equivalent((u.m, u.s, u.kg))
    assert u.ms.is_equivalent((u.m, u.s, u.kg))
    assert u.g.is_equivalent((u.m, u.s, u.kg))
    assert not u.L.is_equivalent((u.m, u.s, u.kg))
    assert not (u.km / u.s).is_equivalent((u.m, u.s, u.kg))


def test_parallax():
    a = u.arcsecond.to(u.pc, 10, u.parallax())
    assert_allclose(a, 0.10, rtol=1.0e-12)
    b = u.pc.to(u.arcsecond, a, u.parallax())
    assert_allclose(b, 10, rtol=1.0e-12)

    a = u.arcminute.to(u.au, 1, u.parallax())
    assert_allclose(a, 3437.746770785, rtol=1.0e-12)
    b = u.au.to(u.arcminute, a, u.parallax())
    assert_allclose(b, 1, rtol=1.0e-12)

    val = (-1 * u.mas).to(u.pc, u.parallax())
    assert np.isnan(val.value)

    val = (-1 * u.mas).to_value(u.pc, u.parallax())
    assert np.isnan(val)


def test_parallax2():
    a = u.arcsecond.to(u.pc, [0.1, 2.5], u.parallax())
    assert_allclose(a, [10, 0.4], rtol=1.0e-12)


def test_spectral():
    a = u.AA.to(u.Hz, 1, u.spectral())
    assert_allclose(a, 2.9979245799999995e18)
    b = u.Hz.to(u.AA, a, u.spectral())
    assert_allclose(b, 1)

    a = u.AA.to(u.MHz, 1, u.spectral())
    assert_allclose(a, 2.9979245799999995e12)
    b = u.MHz.to(u.AA, a, u.spectral())
    assert_allclose(b, 1)

    a = u.m.to(u.Hz, 1, u.spectral())
    assert_allclose(a, 2.9979245799999995e8)
    b = u.Hz.to(u.m, a, u.spectral())
    assert_allclose(b, 1)


def test_spectral2():
    a = u.nm.to(u.J, 500, u.spectral())
    assert_allclose(a, 3.972891366538605e-19)
    b = u.J.to(u.nm, a, u.spectral())
    assert_allclose(b, 500)

    a = u.AA.to(u.Hz, 1, u.spectral())
    b = u.Hz.to(u.J, a, u.spectral())
    c = u.AA.to(u.J, 1, u.spectral())
    assert_allclose(b, c)

    c = u.J.to(u.Hz, b, u.spectral())
    assert_allclose(a, c)


def test_spectral3():
    a = u.nm.to(u.Hz, [1000, 2000], u.spectral())
    assert_allclose(a, [2.99792458e14, 1.49896229e14])


@pytest.mark.parametrize(
    ("in_val", "in_unit"),
    [
        ([0.1, 5000.0, 10000.0], u.AA),
        ([1e5, 2.0, 1.0], u.micron**-1),
        ([2.99792458e19, 5.99584916e14, 2.99792458e14], u.Hz),
        ([1.98644568e-14, 3.97289137e-19, 1.98644568e-19], u.J),
    ],
)
def test_spectral4(in_val, in_unit):
    """Wave number conversion w.r.t. wavelength, freq, and energy."""
    # Spectroscopic and angular
    out_units = [u.micron**-1, u.radian / u.micron]
    answers = [[1e5, 2.0, 1.0], [6.28318531e05, 12.5663706, 6.28318531]]

    for out_unit, ans in zip(out_units, answers):
        # Forward
        a = in_unit.to(out_unit, in_val, u.spectral())
        assert_allclose(a, ans)

        # Backward
        b = out_unit.to(in_unit, ans, u.spectral())
        assert_allclose(b, in_val)


@pytest.mark.parametrize(
    "wav", (3500 * u.AA, 8.5654988e14 * u.Hz, 1 / (3500 * u.AA), 5.67555959e-19 * u.J)
)
def test_spectraldensity2(wav):
    # flux density
    flambda = u.erg / u.angstrom / u.cm**2 / u.s
    fnu = u.erg / u.Hz / u.cm**2 / u.s

    a = flambda.to(fnu, 1, u.spectral_density(wav))
    assert_allclose(a, 4.086160166177361e-12)

    # integrated flux
    f_int = u.erg / u.cm**2 / u.s
    phot_int = u.ph / u.cm**2 / u.s

    a = f_int.to(phot_int, 1, u.spectral_density(wav))
    assert_allclose(a, 1.7619408e11)

    a = phot_int.to(f_int, 1, u.spectral_density(wav))
    assert_allclose(a, 5.67555959e-12)

    # luminosity density
    llambda = u.erg / u.angstrom / u.s
    lnu = u.erg / u.Hz / u.s

    a = llambda.to(lnu, 1, u.spectral_density(wav))
    assert_allclose(a, 4.086160166177361e-12)

    a = lnu.to(llambda, 1, u.spectral_density(wav))
    assert_allclose(a, 2.44728537142857e11)


def test_spectraldensity3():
    # Define F_nu in Jy
    f_nu = u.Jy

    # Define F_lambda in ergs / cm^2 / s / micron
    f_lambda = u.erg / u.cm**2 / u.s / u.micron

    # 1 GHz
    one_ghz = u.Quantity(1, u.GHz)

    # Convert to ergs / cm^2 / s / Hz
    assert_allclose(f_nu.to(u.erg / u.cm**2 / u.s / u.Hz, 1.0), 1.0e-23, 10)

    # Convert to ergs / cm^2 / s at 10 Ghz
    assert_allclose(
        f_nu.to(
            u.erg / u.cm**2 / u.s, 1.0, equivalencies=u.spectral_density(one_ghz * 10)
        ),
        1.0e-13,
    )

    # Convert to F_lambda at 1 Ghz
    assert_allclose(
        f_nu.to(f_lambda, 1.0, equivalencies=u.spectral_density(one_ghz)),
        3.335640951981521e-20,
    )

    # Convert to Jy at 1 Ghz
    assert_allclose(
        f_lambda.to(u.Jy, 1.0, equivalencies=u.spectral_density(one_ghz)),
        1.0 / 3.335640951981521e-20,
    )

    # Convert to ergs / cm^2 / s at 10 microns
    assert_allclose(
        f_lambda.to(
            u.erg / u.cm**2 / u.s,
            1.0,
            equivalencies=u.spectral_density(u.Quantity(10, u.micron)),
        ),
        10.0,
    )


def test_spectraldensity4():
    """PHOTLAM and PHOTNU conversions."""
    flam = u.erg / (u.cm**2 * u.s * u.AA)
    fnu = u.erg / (u.cm**2 * u.s * u.Hz)
    photlam = u.photon / (u.cm**2 * u.s * u.AA)
    photnu = u.photon / (u.cm**2 * u.s * u.Hz)

    wave = u.Quantity([4956.8, 4959.55, 4962.3], u.AA)
    flux_photlam = [9.7654e-3, 1.003896e-2, 9.78473e-3]
    flux_photnu = [8.00335589e-14, 8.23668949e-14, 8.03700310e-14]
    flux_flam = [3.9135e-14, 4.0209e-14, 3.9169e-14]
    flux_fnu = [3.20735792e-25, 3.29903646e-25, 3.21727226e-25]
    flux_jy = [3.20735792e-2, 3.29903646e-2, 3.21727226e-2]
    flux_stmag = [12.41858665, 12.38919182, 12.41764379]
    flux_abmag = [12.63463143, 12.60403221, 12.63128047]

    # PHOTLAM <--> FLAM
    assert_allclose(
        photlam.to(flam, flux_photlam, u.spectral_density(wave)), flux_flam, rtol=1e-6
    )
    assert_allclose(
        flam.to(photlam, flux_flam, u.spectral_density(wave)), flux_photlam, rtol=1e-6
    )

    # PHOTLAM <--> FNU
    assert_allclose(
        photlam.to(fnu, flux_photlam, u.spectral_density(wave)), flux_fnu, rtol=1e-6
    )
    assert_allclose(
        fnu.to(photlam, flux_fnu, u.spectral_density(wave)), flux_photlam, rtol=1e-6
    )

    # PHOTLAM <--> Jy
    assert_allclose(
        photlam.to(u.Jy, flux_photlam, u.spectral_density(wave)), flux_jy, rtol=1e-6
    )
    assert_allclose(
        u.Jy.to(photlam, flux_jy, u.spectral_density(wave)), flux_photlam, rtol=1e-6
    )

    # PHOTLAM <--> PHOTNU
    assert_allclose(
        photlam.to(photnu, flux_photlam, u.spectral_density(wave)),
        flux_photnu,
        rtol=1e-6,
    )
    assert_allclose(
        photnu.to(photlam, flux_photnu, u.spectral_density(wave)),
        flux_photlam,
        rtol=1e-6,
    )

    # PHOTNU <--> FNU
    assert_allclose(
        photnu.to(fnu, flux_photnu, u.spectral_density(wave)), flux_fnu, rtol=1e-6
    )
    assert_allclose(
        fnu.to(photnu, flux_fnu, u.spectral_density(wave)), flux_photnu, rtol=1e-6
    )

    # PHOTNU <--> FLAM
    assert_allclose(
        photnu.to(flam, flux_photnu, u.spectral_density(wave)), flux_flam, rtol=1e-6
    )
    assert_allclose(
        flam.to(photnu, flux_flam, u.spectral_density(wave)), flux_photnu, rtol=1e-6
    )

    # PHOTLAM <--> STMAG
    assert_allclose(
        photlam.to(u.STmag, flux_photlam, u.spectral_density(wave)),
        flux_stmag,
        rtol=1e-6,
    )
    assert_allclose(
        u.STmag.to(photlam, flux_stmag, u.spectral_density(wave)),
        flux_photlam,
        rtol=1e-6,
    )

    # PHOTLAM <--> ABMAG
    assert_allclose(
        photlam.to(u.ABmag, flux_photlam, u.spectral_density(wave)),
        flux_abmag,
        rtol=1e-6,
    )
    assert_allclose(
        u.ABmag.to(photlam, flux_abmag, u.spectral_density(wave)),
        flux_photlam,
        rtol=1e-6,
    )


def test_spectraldensity5():
    """Test photon luminosity density conversions."""
    L_la = u.erg / (u.s * u.AA)
    L_nu = u.erg / (u.s * u.Hz)
    phot_L_la = u.photon / (u.s * u.AA)
    phot_L_nu = u.photon / (u.s * u.Hz)

    wave = u.Quantity([4956.8, 4959.55, 4962.3], u.AA)
    flux_phot_L_la = [9.7654e-3, 1.003896e-2, 9.78473e-3]
    flux_phot_L_nu = [8.00335589e-14, 8.23668949e-14, 8.03700310e-14]
    flux_L_la = [3.9135e-14, 4.0209e-14, 3.9169e-14]
    flux_L_nu = [3.20735792e-25, 3.29903646e-25, 3.21727226e-25]

    # PHOTLAM <--> FLAM
    assert_allclose(
        phot_L_la.to(L_la, flux_phot_L_la, u.spectral_density(wave)),
        flux_L_la,
        rtol=1e-6,
    )
    assert_allclose(
        L_la.to(phot_L_la, flux_L_la, u.spectral_density(wave)),
        flux_phot_L_la,
        rtol=1e-6,
    )

    # PHOTLAM <--> FNU
    assert_allclose(
        phot_L_la.to(L_nu, flux_phot_L_la, u.spectral_density(wave)),
        flux_L_nu,
        rtol=1e-6,
    )
    assert_allclose(
        L_nu.to(phot_L_la, flux_L_nu, u.spectral_density(wave)),
        flux_phot_L_la,
        rtol=1e-6,
    )

    # PHOTLAM <--> PHOTNU
    assert_allclose(
        phot_L_la.to(phot_L_nu, flux_phot_L_la, u.spectral_density(wave)),
        flux_phot_L_nu,
        rtol=1e-6,
    )
    assert_allclose(
        phot_L_nu.to(phot_L_la, flux_phot_L_nu, u.spectral_density(wave)),
        flux_phot_L_la,
        rtol=1e-6,
    )

    # PHOTNU <--> FNU
    assert_allclose(
        phot_L_nu.to(L_nu, flux_phot_L_nu, u.spectral_density(wave)),
        flux_L_nu,
        rtol=1e-6,
    )
    assert_allclose(
        L_nu.to(phot_L_nu, flux_L_nu, u.spectral_density(wave)),
        flux_phot_L_nu,
        rtol=1e-6,
    )

    # PHOTNU <--> FLAM
    assert_allclose(
        phot_L_nu.to(L_la, flux_phot_L_nu, u.spectral_density(wave)),
        flux_L_la,
        rtol=1e-6,
    )
    assert_allclose(
        L_la.to(phot_L_nu, flux_L_la, u.spectral_density(wave)),
        flux_phot_L_nu,
        rtol=1e-6,
    )


def test_spectraldensity6():
    """Test surface brightness conversions."""
    slam = u.erg / (u.cm**2 * u.s * u.AA * u.sr)
    snu = u.erg / (u.cm**2 * u.s * u.Hz * u.sr)

    wave = u.Quantity([4956.8, 4959.55, 4962.3], u.AA)
    sb_flam = [3.9135e-14, 4.0209e-14, 3.9169e-14]
    sb_fnu = [3.20735792e-25, 3.29903646e-25, 3.21727226e-25]

    # S(nu) <--> S(lambda)
    assert_allclose(snu.to(slam, sb_fnu, u.spectral_density(wave)), sb_flam, rtol=1e-6)
    assert_allclose(slam.to(snu, sb_flam, u.spectral_density(wave)), sb_fnu, rtol=1e-6)


@pytest.mark.parametrize(
    ("from_unit", "to_unit"),
    [
        (u.ph / u.cm**2 / u.s, (u.cm * u.cm * u.s) ** -1),
        (u.ph / u.cm**2 / u.s, u.erg / (u.cm * u.cm * u.s * u.keV)),
        (u.erg / u.cm**2 / u.s, (u.cm * u.cm * u.s) ** -1),
        (u.erg / u.cm**2 / u.s, u.erg / (u.cm * u.cm * u.s * u.keV)),
    ],
)
def test_spectraldensity_not_allowed(from_unit, to_unit):
    """Not allowed to succeed as
    per https://github.com/astropy/astropy/pull/10015
    """
    with pytest.raises(u.UnitConversionError, match="not convertible"):
        from_unit.to(to_unit, 1, u.spectral_density(1 * u.AA))

    # The other way
    with pytest.raises(u.UnitConversionError, match="not convertible"):
        to_unit.to(from_unit, 1, u.spectral_density(1 * u.AA))


def test_equivalent_units():
    from astropy.units import imperial

    with u.add_enabled_units(imperial):
        units = u.g.find_equivalent_units()
        units_set = set(units)
        match = {
            u.M_e, u.M_p, u.g, u.kg, u.solMass, u.t, u.u, u.M_earth,
            u.M_jup, imperial.oz, imperial.lb, imperial.st, imperial.ton,
            imperial.slug,
        }  # fmt: skip
        assert units_set == match

    r = repr(units)
    assert r.count("\n") == len(units) + 2


def test_equivalent_units2():
    units = set(u.Hz.find_equivalent_units(u.spectral()))
    match = {
        u.AU, u.Angstrom, u.Hz, u.J, u.Ry, u.cm, u.eV, u.erg, u.lyr, u.lsec,
        u.m, u.micron, u.pc, u.solRad, u.Bq, u.Ci, u.k, u.earthRad,
        u.jupiterRad, u.foe,
    }  # fmt: skip
    assert units == match

    from astropy.units import imperial

    with u.add_enabled_units(imperial):
        units = set(u.Hz.find_equivalent_units(u.spectral()))
        match = {
            u.AU, u.Angstrom, imperial.BTU, u.Hz, u.J, u.Ry,
            imperial.cal, u.cm, u.eV, u.erg, imperial.ft, imperial.fur,
            imperial.inch, imperial.kcal, u.lyr, u.m, imperial.mi, u.lsec,
            imperial.mil, u.micron, u.pc, u.solRad, imperial.yd, u.Bq, u.Ci,
            imperial.nmi, u.k, u.earthRad, u.jupiterRad, u.foe,
        }  # fmt: skip
        assert units == match

    units = set(u.Hz.find_equivalent_units(u.spectral()))
    match = {
        u.AU, u.Angstrom, u.Hz, u.J, u.Ry, u.cm, u.eV, u.erg, u.lyr, u.lsec,
        u.m, u.micron, u.pc, u.solRad, u.Bq, u.Ci, u.k, u.earthRad,
        u.jupiterRad, u.foe,
    }  # fmt: skip
    assert units == match


def test_trivial_equivalency():
    assert u.m.to(u.kg, equivalencies=[(u.m, u.kg)]) == 1.0


def test_invalid_equivalency():
    with pytest.raises(ValueError):
        u.m.to(u.kg, equivalencies=[(u.m,)])

    with pytest.raises(ValueError):
        u.m.to(u.kg, equivalencies=[(u.m, 5.0)])


def test_irrelevant_equivalency():
    with pytest.raises(u.UnitsError):
        u.m.to(u.kg, equivalencies=[(u.m, u.l)])


def test_brightness_temperature():
    omega_B = np.pi * (50 * u.arcsec) ** 2
    nu = u.GHz * 5
    tb = 7.052587837212582 * u.K
    np.testing.assert_almost_equal(
        tb.value,
        (1 * u.Jy).to_value(
            u.K, equivalencies=u.brightness_temperature(nu, beam_area=omega_B)
        ),
    )
    np.testing.assert_almost_equal(
        1.0,
        tb.to_value(
            u.Jy, equivalencies=u.brightness_temperature(nu, beam_area=omega_B)
        ),
    )


def test_surfacebrightness():
    sb = 50 * u.MJy / u.sr
    k = sb.to(u.K, u.brightness_temperature(50 * u.GHz))
    np.testing.assert_almost_equal(k.value, 0.650965, 5)
    assert k.unit.is_equivalent(u.K)


def test_beam():
    # pick a beam area: 2 pi r^2 = area of a Gaussina with sigma=50 arcsec
    omega_B = 2 * np.pi * (50 * u.arcsec) ** 2
    new_beam = (5 * u.beam).to(u.sr, u.equivalencies.beam_angular_area(omega_B))
    np.testing.assert_almost_equal(omega_B.to(u.sr).value * 5, new_beam.value)
    assert new_beam.unit.is_equivalent(u.sr)

    # make sure that it's still consistent with 5 beams
    nbeams = new_beam.to(u.beam, u.equivalencies.beam_angular_area(omega_B))
    np.testing.assert_almost_equal(nbeams.value, 5)

    # test inverse beam equivalency
    # (this is just a sanity check that the equivalency is defined;
    # it's not for testing numerical consistency)
    (5 / u.beam).to(1 / u.sr, u.equivalencies.beam_angular_area(omega_B))

    # test practical case
    # (this is by far the most important one)
    flux_density = (5 * u.Jy / u.beam).to(
        u.MJy / u.sr, u.equivalencies.beam_angular_area(omega_B)
    )

    np.testing.assert_almost_equal(flux_density.value, 13.5425483146382)


def test_thermodynamic_temperature():
    nu = 143 * u.GHz
    tb = 0.0026320501262630277 * u.K
    eq = u.thermodynamic_temperature(nu, T_cmb=2.7255 * u.K)
    np.testing.assert_almost_equal(
        tb.value, (1 * (u.MJy / u.sr)).to_value(u.K, equivalencies=eq)
    )
    np.testing.assert_almost_equal(1.0, tb.to_value(u.MJy / u.sr, equivalencies=eq))


def test_equivalency_context():
    with u.set_enabled_equivalencies(u.dimensionless_angles()):
        phase = u.Quantity(1.0, u.cycle)
        assert_allclose(np.exp(1j * phase), 1.0)
        Omega = u.cycle / (1.0 * u.minute)
        assert_allclose(np.exp(1j * Omega * 60.0 * u.second), 1.0)
        # ensure we can turn off equivalencies even within the scope
        with pytest.raises(u.UnitsError):
            phase.to(1, equivalencies=None)

        # test the manager also works in the Quantity constructor.
        q1 = u.Quantity(phase, u.dimensionless_unscaled)
        assert_allclose(q1.value, u.cycle.to(u.radian))

        # and also if we use a class that happens to have a unit attribute.
        class MyQuantityLookalike(np.ndarray):
            pass

        mylookalike = np.array(1.0).view(MyQuantityLookalike)
        mylookalike.unit = "cycle"
        # test the manager also works in the Quantity constructor.
        q2 = u.Quantity(mylookalike, u.dimensionless_unscaled)
        assert_allclose(q2.value, u.cycle.to(u.radian))

    with u.set_enabled_equivalencies(u.spectral()):
        u.GHz.to(u.cm)
        eq_on = u.GHz.find_equivalent_units()
        with pytest.raises(u.UnitsError):
            u.GHz.to(u.cm, equivalencies=None)

    # without equivalencies, we should find a smaller (sub)set
    eq_off = u.GHz.find_equivalent_units()
    assert all(eq in set(eq_on) for eq in eq_off)
    assert set(eq_off) < set(eq_on)

    # Check the equivalency manager also works in ufunc evaluations,
    # not just using (wrong) scaling. [#2496]
    l2v = u.doppler_optical(6000 * u.angstrom)
    l1 = 6010 * u.angstrom
    assert l1.to(u.km / u.s, equivalencies=l2v) > 100.0 * u.km / u.s
    with u.set_enabled_equivalencies(l2v):
        assert l1 > 100.0 * u.km / u.s
        assert abs((l1 - 500.0 * u.km / u.s).to(u.angstrom)) < 1.0 * u.km / u.s


def test_equivalency_context_manager():
    base_registry = u.get_current_unit_registry()

    def just_to_from_units(equivalencies):
        return [(equiv[0], equiv[1]) for equiv in equivalencies]

    tf_dimensionless_angles = just_to_from_units(u.dimensionless_angles())
    tf_spectral = just_to_from_units(u.spectral())

    # <=1 b/c might have the dimensionless_redshift equivalency enabled.
    assert len(base_registry.equivalencies) <= 1

    with u.set_enabled_equivalencies(u.dimensionless_angles()):
        new_registry = u.get_current_unit_registry()
        assert set(just_to_from_units(new_registry.equivalencies)) == set(
            tf_dimensionless_angles
        )
        assert set(new_registry.all_units) == set(base_registry.all_units)
        with u.set_enabled_equivalencies(u.spectral()):
            newer_registry = u.get_current_unit_registry()
            assert set(just_to_from_units(newer_registry.equivalencies)) == set(
                tf_spectral
            )
            assert set(newer_registry.all_units) == set(base_registry.all_units)

        assert set(just_to_from_units(new_registry.equivalencies)) == set(
            tf_dimensionless_angles
        )
        assert set(new_registry.all_units) == set(base_registry.all_units)
        with u.add_enabled_equivalencies(u.spectral()):
            newer_registry = u.get_current_unit_registry()
            assert set(just_to_from_units(newer_registry.equivalencies)) == set(
                tf_dimensionless_angles
            ) | set(tf_spectral)
            assert set(newer_registry.all_units) == set(base_registry.all_units)

    assert base_registry is u.get_current_unit_registry()


def test_temperature():
    from astropy.units.imperial import deg_F, deg_R

    t_k = 0 * u.K
    assert_allclose(t_k.to_value(u.deg_C, u.temperature()), -273.15)
    assert_allclose(t_k.to_value(deg_F, u.temperature()), -459.67)
    t_k = 20 * deg_F
    assert_allclose(t_k.to_value(deg_R, u.temperature()), 479.67)
    t_k = 20 * deg_R
    assert_allclose(t_k.to_value(deg_F, u.temperature()), -439.67)
    t_k = 20 * u.deg_C
    assert_allclose(t_k.to_value(deg_R, u.temperature()), 527.67)
    t_k = 20 * deg_R
    assert_allclose(t_k.to_value(u.deg_C, u.temperature()), -262.039, atol=0.01)


def test_temperature_energy():
    x = 1000 * u.K
    y = (x * constants.k_B).to(u.keV)
    assert_allclose(x.to_value(u.keV, u.temperature_energy()), y.value)
    assert_allclose(y.to_value(u.K, u.temperature_energy()), x.value)


def test_molar_mass_amu():
    x = 1 * (u.g / u.mol)
    y = 1 * u.u
    assert_allclose(x.to_value(u.u, u.molar_mass_amu()), y.value)
    assert_allclose(y.to_value(u.g / u.mol, u.molar_mass_amu()), x.value)
    with pytest.raises(u.UnitsError):
        x.to(u.u)


def test_compose_equivalencies():
    x = u.Unit("arcsec").compose(units=(u.pc,), equivalencies=u.parallax())
    assert x[0] == u.pc

    x = u.Unit("2 arcsec").compose(units=(u.pc,), equivalencies=u.parallax())
    assert x[0] == u.Unit(0.5 * u.pc)

    x = u.degree.compose(equivalencies=u.dimensionless_angles())
    assert u.Unit(u.degree.to(u.radian)) in x

    x = (u.nm).compose(
        units=(u.m, u.s), equivalencies=u.doppler_optical(0.55 * u.micron)
    )
    for y in x:
        if y.bases == [u.m, u.s]:
            assert y.powers == [1, -1]
            assert_allclose(
                y.scale,
                u.nm.to(u.m / u.s, equivalencies=u.doppler_optical(0.55 * u.micron)),
            )
            break
    else:
        raise AssertionError("Didn't find speed in compose results")


def test_pixel_scale():
    pix = 75 * u.pix
    asec = 30 * u.arcsec

    pixscale = 0.4 * u.arcsec / u.pix
    pixscale2 = 2.5 * u.pix / u.arcsec

    assert_quantity_allclose(pix.to(u.arcsec, u.pixel_scale(pixscale)), asec)
    assert_quantity_allclose(pix.to(u.arcmin, u.pixel_scale(pixscale)), asec)

    assert_quantity_allclose(pix.to(u.arcsec, u.pixel_scale(pixscale2)), asec)
    assert_quantity_allclose(pix.to(u.arcmin, u.pixel_scale(pixscale2)), asec)

    assert_quantity_allclose(asec.to(u.pix, u.pixel_scale(pixscale)), pix)
    assert_quantity_allclose(asec.to(u.pix, u.pixel_scale(pixscale2)), pix)


def test_pixel_scale_invalid_scale_unit():
    pixscale = 0.4 * u.arcsec
    pixscale2 = 0.4 * u.arcsec / u.pix**2

    with pytest.raises(u.UnitsError, match="pixel dimension"):
        u.pixel_scale(pixscale)
    with pytest.raises(u.UnitsError, match="pixel dimension"):
        u.pixel_scale(pixscale2)


def test_pixel_scale_acceptable_scale_unit():
    pix = 75 * u.pix
    v = 3000 * (u.cm / u.s)

    pixscale = 0.4 * (u.m / u.s / u.pix)
    pixscale2 = 2.5 * (u.pix / (u.m / u.s))

    assert_quantity_allclose(pix.to(u.m / u.s, u.pixel_scale(pixscale)), v)
    assert_quantity_allclose(pix.to(u.km / u.s, u.pixel_scale(pixscale)), v)

    assert_quantity_allclose(pix.to(u.m / u.s, u.pixel_scale(pixscale2)), v)
    assert_quantity_allclose(pix.to(u.km / u.s, u.pixel_scale(pixscale2)), v)

    assert_quantity_allclose(v.to(u.pix, u.pixel_scale(pixscale)), pix)
    assert_quantity_allclose(v.to(u.pix, u.pixel_scale(pixscale2)), pix)


def test_plate_scale():
    mm = 1.5 * u.mm
    asec = 30 * u.arcsec

    platescale = 20 * u.arcsec / u.mm
    platescale2 = 0.05 * u.mm / u.arcsec

    assert_quantity_allclose(mm.to(u.arcsec, u.plate_scale(platescale)), asec)
    assert_quantity_allclose(mm.to(u.arcmin, u.plate_scale(platescale)), asec)

    assert_quantity_allclose(mm.to(u.arcsec, u.plate_scale(platescale2)), asec)
    assert_quantity_allclose(mm.to(u.arcmin, u.plate_scale(platescale2)), asec)

    assert_quantity_allclose(asec.to(u.mm, u.plate_scale(platescale)), mm)
    assert_quantity_allclose(asec.to(u.mm, u.plate_scale(platescale2)), mm)


def test_equivelency():
    ps = u.pixel_scale(10 * u.arcsec / u.pix)
    assert isinstance(ps, Equivalency)
    assert isinstance(ps.name, list)
    assert len(ps.name) == 1
    assert ps.name[0] == "pixel_scale"
    assert isinstance(ps.kwargs, list)
    assert len(ps.kwargs) == 1
    assert ps.kwargs[0] == {"pixscale": 10 * u.arcsec / u.pix}


def test_add_equivelencies():
    e1 = u.pixel_scale(10 * u.arcsec / u.pixel) + u.temperature_energy()
    assert isinstance(e1, Equivalency)
    assert e1.name == ["pixel_scale", "temperature_energy"]
    assert isinstance(e1.kwargs, list)
    assert e1.kwargs == [{"pixscale": 10 * u.arcsec / u.pix}, {}]

    e2 = u.pixel_scale(10 * u.arcsec / u.pixel) + [1, 2, 3]
    assert isinstance(e2, list)


def test_pprint():
    pprint_class = u.UnitBase.EquivalentUnitsList
    equiv_units_to_Hz = u.Hz.find_equivalent_units()
    assert pprint_class.__repr__(equiv_units_to_Hz).splitlines() == [
        "  Primary name | Unit definition | Aliases     ",
        "[",
        "  Bq           | 1 / s           | becquerel    ,",
        "  Ci           | 3.7e+10 / s     | curie        ,",
        "  Hz           | 1 / s           | Hertz, hertz ,",
        "]",
    ]
    assert (
        pprint_class._repr_html_(equiv_units_to_Hz) == '<table style="width:50%">'
        "<tr><th>Primary name</th><th>Unit definition</th>"
        "<th>Aliases</th></tr>"
        "<tr><td>Bq</td><td>1 / s</td><td>becquerel</td></tr>"
        "<tr><td>Ci</td><td>3.7e+10 / s</td><td>curie</td></tr>"
        "<tr><td>Hz</td><td>1 / s</td><td>Hertz, hertz</td></tr></table>"
    )


def test_spectral_density_factor_deprecation():
    with pytest.warns(
        AstropyDeprecationWarning,
        match=(
            r'^"factor" was deprecated in version 7\.0 and will be removed in a future '
            r'version\. \n        Use "wav" as a "Quantity" instead\.$'
        ),
    ):
        a = (u.erg / u.angstrom / u.cm**2 / u.s).to(
            u.erg / u.Hz / u.cm**2 / u.s, 1, u.spectral_density(u.AA, factor=3500)
        )
    assert_quantity_allclose(a, 4.086160166177361e-12)


def test_magnetic_flux_field():
    H = 1 * u.A / u.m
    B = (H * constants.mu0).to(u.T)
    assert_allclose(H.to_value(u.T, u.magnetic_flux_field()), B.value)
    assert_allclose(B.to_value(u.A / u.m, u.magnetic_flux_field()), H.value)

    H = 1 * u.Oe
    B = 1 * u.G
    assert_allclose(H.to_value(u.G, u.magnetic_flux_field()), 1)
    assert_allclose(B.to_value(u.Oe, u.magnetic_flux_field()), 1)
    assert_allclose(H.to_value(u.G, u.magnetic_flux_field(mu_r=0.8)), 0.8)
    assert_allclose(B.to_value(u.Oe, u.magnetic_flux_field(mu_r=0.8)), 1.25)
