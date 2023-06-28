#!/usr/bin/env python
# coding: utf-8

from pyiron_base import Project
from pyiron_base import PythonTemplateJob, JobType, ImportAlarm
import os
import yaml
import numpy as np
from skimage.exposure import rescale_intensity
import warnings

try:
    from cerberus import Validator
    from msiplib.io import read_image
    from msiplib.unit_cell_from_real_space import find_real_space_vectors

    import_alarm = ImportAlarm()
except ImportError:
    import_alarm = ImportAlarm(
        "This job type requires ceberus and msiplib\n Please contact Benjamin Berkels to have msiplib!"
    )


class UCVExtractor(PythonTemplateJob):
    @import_alarm
    def __init__(self, project, job_name):
        super().__init__(project, job_name)
        self.input._imagearray = None  # user is not allowed ulter this variable

    @property
    def image_array(self):  # user have access to see but not ulter
        return self.input._imagearray

    @image_array.setter  # allowes setting image_array (ultering it as well)
    def image_array(self, val):
        if isinstance(val, str):
            self.input._imagearray = read_image(val, as_gray=not val.endswith(".nc"))
        elif isinstance(val, np.ndarray):
            self.input._imagearray = val
        else:
            raise ValueError("Input valid image or image path!")

    def validate_ready_to_run(self):
        params = (
            self.input.to_builtin()
        )  # convert it to a normal dictionary instead of input dictionary object
        del params["_imagearray"]
        schema = {
            "input_file": {
                "type": "string",
            },
            "save_directory": {
                "required": True,
                "type": "string",
            },
            "save_name": {
                "required": True,
                "type": "string",
            },
            "uniform_prefilter_size": {
                "type": "integer",
                "min": 0,
            },
            "energy_exclusion_factor": {
                "type": "float",
                "min": 1.01,
            },
        }

        vali = Validator(schema)
        if not vali.validate(params, schema):
            raise ValueError(f"Validating parameter file failed.\n{vali.errors}")
        if self.image_array is None and "input_file" not in params:
            raise ValueError("Missing image file!")
        elif self.image_array is None:
            self.image_array = self.input.input_file
        elif "input_file" in params:
            warnings.warn(
                "image_array and input.input_file defined - taking the image array!"
            )

    def run_static(self):
        params = self.input
        path = os.path.expandvars(params["save_directory"])
        im = rescale_intensity(self.image_array, out_range=(0.0, 1.0))
        name = params["save_name"]
        uniform_prefilter_size_setting = (
            {"uniform_prefilter_size": params["uniform_prefilter_size"]}
            if "uniform_prefilter_size" in params
            else {}
        )
        energy_exclusion_factor_setting = (
            {"energy_exclusion_factor": params["energy_exclusion_factor"]}
            if "energy_exclusion_factor" in params
            else {}
        )

        self.output.vec = find_real_space_vectors(
            im,
            path,
            name,
            **(uniform_prefilter_size_setting),
            **(energy_exclusion_factor_setting),
            plot=False,
            write_to_file=False,
        )
        self.to_hdf()
        self.status.finished = True
