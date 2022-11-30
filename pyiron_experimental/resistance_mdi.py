# coding: utf-8
# Copyright (c) Max-Planck-Institut für Eisenforschung GmbH - Computational Materials Design (CM) Department
# Distributed under the terms of "New BSD License", see the LICENSE file.
"""
Template class to define jobs
"""

# from pyiron_base.jobs.job.template (if not installed experimental)
from pyiron_base.job.template import TemplateJob
from autonoexp.measurement_devices import Resistance
import autonoexp.gaussian_process as gp

import numpy as np


class ResistanceGP(TemplateJob):
    def __init__(self, project, job_name):
        super().__init__(project, job_name)
        self._python_only_job = True
        # to be discussed, no classes, only int/float/str/lists/dict
        # alternative: self.input.exp_user = None
        self.input["exp_user"] = None
        self.input["measurement_device"] = str(type(Resistance))
        self.input["sample_id"] = 12345
        self.input["measure_indices"] = [5, 157, 338, 177, 188]
        self.input["sample_file"] = None
        self.input["max_gp_iterations"] = 10
        self.input["element_column_ids"] = None

    def _check_if_input_should_be_written(self):
        return False

    # Change validity of jobs after the fact
    # def validity(self):

    # def postprocess_xrd(self):
    #     cs = crystal_structure_analysis(self.output['xrd_measurement'])
    #     self.output['crystal_structure'] = cs

    def run_static(self):
        self.device = Resistance(self.input.sample_file,
                                 self.input.element_column_ids)

        X0, y0 = self.device.get_initial_measurement(
            indices=self.input.measure_indices, target_property="Resistance"
        )

        # Initialize Gaussian process
        model = gp.GP(X0, np.log(y0), self.device.elements)

        # Get all elemental compositions as variables for prediction
        X = self.device.get_variables()

        model.predict(X)

        max_cov, index_max_cov = model.get_max_covariance()

        print("Max covariance and index = {} [{}]".format(max_cov,
                                                          index_max_cov))

        X_tmp, y_tmp = self.device.get_measurement(
            indices=[index_max_cov], target_property="Resistance"
        )

        model.update_Xy(X_tmp, y_tmp)
        model.predict(X)

        max_cov, index_max_cov = model.get_max_covariance()

        # think about: run_interactive, for
        for i in range(self.input.max_gp_iterations):
            # while(max_cov > VAL):

            print("Max covariance and index = {} [{}]".format(max_cov,
                                                              index_max_cov))

            X_tmp, y_tmp = self.device.get_measurement(
                indices=[index_max_cov], target_property="Resistance"
            )
            print("New measurement shape = {}".format(X_tmp.shape))
            model.update_Xy(X_tmp, y_tmp)

            prediction = model.predict(X)

            max_cov, index_max_cov = model.get_max_covariance()
            print("IDX max cov = {}".format(index_max_cov))

        # ideal: dataframe
        self.output["elements"] = list(
            self.device.elements
        )  # needs to work without list
        self.output["element_concentration"] = X_tmp
        self.output["resistance_measured"] = y_tmp
        self.output["measurement_indices"] = self.device.measured_ids
        self.output["resistance_prediction"] = np.exp(model.mu)
        self.output["covariance"] = model.cov
        self.output["prediction"] = prediction
        # self.postprocess_xrd()

        # self.output['resistance_model'] = model.
        self.to_hdf()
        self.status.finished = True
