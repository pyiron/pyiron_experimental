# coding: utf-8
# Copyright (c) Max-Planck-Institut für Eisenforschung GmbH - Computational Materials Design (CM) Department
# Distributed under the terms of "New BSD License", see the LICENSE file.
"""
Template class to define jobs
"""

from pyiron_base.job.template import TemplateJob
from autonoexp.measurement_devices import Resistance
import autonoexp.gaussian_process as gp

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
        self.input["sample_file"] = "Co-Fe-La-Mn-O_coordinates_composition_resistance.csv"
        self.input["max_gp_iterations"] = 10
        
    def _check_if_input_should_be_written(self):
        return False

    # Change validity of jobs after the fact
    # def validity(self):
        

    def run_static(self):
        device = Resistance(self.input.sample_file)

        X0, y0 = device.get_initial_measurement(indices=self.input.measure_indices)

        # Initialize Gaussian process
        model = gp.GP(X0, y0, device.elements)

        # Get all elemental compositions as variables for prediction
        X = device.get_variables()

        model.predict(X)

        max_cov, index_max_cov = model.get_max_covariance()

        print("Max covariance and index = {} [{}]".format(max_cov, index_max_cov))
        
        X_tmp, y_tmp = device.get_measurement(indices=[index_max_cov])

        model.update_Xy(X_tmp, y_tmp)
        model.predict(X)

        max_cov, index_max_cov = model.get_max_covariance()

        # think about: run_interactive, for 
        for i in range(self.input.max_gp_iterations):
            #while(max_cov > VAL):

            print("Max covariance and index = {} [{}]".format(max_cov, index_max_cov))

            X_tmp, y_tmp = device.get_measurement(indices=[index_max_cov])
            print("New measurement shape = {}".format(X_tmp.shape))
            model.update_Xy(X_tmp, y_tmp)
            
            model.predict(X)
    
            max_cov, index_max_cov = model.get_max_covariance()
            print("IDX max cov = {}".format(index_max_cov))

        # ideal: dataframe
        self.output['elements'] = list(device.elements) # needs to work without list
        self.output['element_concentration'] = X_tmp
        self.output['resistance_measured'] = y_tmp
        self.output['measurement_indices'] = device.measured_ids
        #self.output['resistance_model'] = model.
        self.to_hdf()
        self.status.finished = True

    def get_dataframe(self):
        import pandas as pd
        df = pd.DataFrame(columns=element + 'resistance', element_concentration, measurement_indices)

        

    
