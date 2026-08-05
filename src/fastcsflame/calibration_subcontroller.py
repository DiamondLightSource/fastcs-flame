from fastcs.attributes import AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Float, Int
from fastcs.methods.command import command
from sympy import solve
from sympy.abc import a, b, c, d

from fastcsflame.flame_controller_attributes import (
    DummyFloatIO,
    DummyFloatIORef,
    DummyIntIO,
    DummyIntIORef,
    SpectrometerWCCIO,
    SpectrommeterWCCIORef,
)
from fastcsflame.spectrometer_telecommunicator import (
    SpectrometerTelecommunicator as SpecTel,
)


class CalibrationSubcontroller(Controller):
    pixel_1_index: AttrRW[int, DummyIntIORef]
    pixel_2_index: AttrRW[int, DummyIntIORef]
    pixel_3_index: AttrRW[int, DummyIntIORef]
    pixel_4_index: AttrRW[int, DummyIntIORef]

    pixel_1_wavelength: AttrRW[float, DummyFloatIORef]
    pixel_2_wavelength: AttrRW[float, DummyFloatIORef]
    pixel_3_wavelength: AttrRW[float, DummyFloatIORef]
    pixel_4_wavelength: AttrRW[float, DummyFloatIORef]

    zero_order_wcc: AttrRW[float, SpectrommeterWCCIORef]
    first_order_wcc: AttrRW[float, SpectrommeterWCCIORef]
    second_order_wcc: AttrRW[float, SpectrommeterWCCIORef]
    third_order_wcc: AttrRW[float, SpectrommeterWCCIORef]

    def __init__(self, spec_tel_obj: SpecTel):
        super().__init__(ios=[DummyIntIO(), DummyFloatIO(), SpectrometerWCCIO()])

        self.pixel_1_index = AttrRW(Int(), io_ref=DummyIntIORef(0))
        self.pixel_2_index = AttrRW(Int(), io_ref=DummyIntIORef(1))
        self.pixel_3_index = AttrRW(Int(), io_ref=DummyIntIORef(2))
        self.pixel_4_index = AttrRW(Int(), io_ref=DummyIntIORef(3))

        self.pixel_1_wavelength = AttrRW(Float(), io_ref=DummyFloatIORef(200.0))
        self.pixel_2_wavelength = AttrRW(Float(), io_ref=DummyFloatIORef(210.0))
        self.pixel_3_wavelength = AttrRW(Float(), io_ref=DummyFloatIORef(220.0))
        self.pixel_4_wavelength = AttrRW(Float(), io_ref=DummyFloatIORef(230.0))

        self.zero_order_wcc = AttrRW(
            Float(), io_ref=SpectrommeterWCCIORef(spec_tel_obj, 0)
        )
        self.first_order_wcc = AttrRW(
            Float(), io_ref=SpectrommeterWCCIORef(spec_tel_obj, 1)
        )
        self.second_order_wcc = AttrRW(
            Float(), io_ref=SpectrommeterWCCIORef(spec_tel_obj, 2)
        )
        self.third_order_wcc = AttrRW(
            Float(), io_ref=SpectrommeterWCCIORef(spec_tel_obj, 3)
        )

    @command()
    async def auto_calibrate(self):
        equations = []
        points = [
            (self.pixel_1_index.get(), self.pixel_1_wavelength.get()),
            (self.pixel_2_index.get(), self.pixel_2_wavelength.get()),
            (self.pixel_3_index.get(), self.pixel_3_wavelength.get()),
            (self.pixel_4_index.get(), self.pixel_4_wavelength.get()),
        ]

        for x, y in points:
            equation = (a * x**3) + (b * x**2) + (c * x) + d - y
            equations.append(equation)

        solutions = solve(equations, a, b, c, d)

        await self.third_order_wcc.put(solutions[0])
        await self.second_order_wcc.put(solutions[1])
        await self.first_order_wcc.put(solutions[2])
        await self.zero_order_wcc.put(solutions[3])
