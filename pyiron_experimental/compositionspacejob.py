import sys
import os
import numpy as np
from compositionspace.datautils import DataPreparation
import pandas as pd
import matplotlib.pylab as plt
from compositionspace.segmentation import CompositionClustering
from compositionspace.postprocessing import DataPostprocess
from pyiron_base import DataContainer
from pyiron_base import GenericJob, ImportAlarm
from pyiron_experimental import Project

class CompositionSpace(GenericJob):
    """
    Add some docs
    """
    def __init__(self, project, job_name):
        super().__init__(project, job_name)
        self.input = DataContainer(self._default_input, table_name="inputdata")
        self._composition_clusters_found = False
        self._data = None
        self._comp = None
        self._post = None
        self.input.analysis = None
        self.input.fileindex=0
        self.input.cluster_id=0
        self.input.plot=False
        self.input.plot3d=False     
        self._input_dict = {}

    @property
    def _default_input(self):
        return {
            "input_path": None,
            #"output_path": None,
            "n_big_slices": 10,
            "voxel_size": 2,
            "bics_clusters": 10,
            "n_phases": 3,
            "ml_models": {
                "name": "GaussianMixture", 
                "GaussianMixture": {
                    "n_components": 3,
                    "max_iter": 100000,
                    "verbose": 0,
                    },
                "RandomForest": {
                    "max_depth": 0,
                    "n_estimators": 0,
                    },
                "DBScan": {
                    "eps": 5,
                    "min_samples": 50,
                    },
            }
        }


    def _create_input(self, indict, datacontainer):
        for key, val in indict.items():
            if key in datacontainer:
                if isinstance(val, dict):
                    self._create_input(indict[key], datacontainer[key])
                else:
                    indict[key] = getattr(datacontainer, key)
        return indict
    
    def write_input(self):
        #prepare data
        indict = self._create_input(self._default_input, self.input)
        indict["output_path"] = self.working_directory
        self._input_dict = indict

    def _prepare_comp(self):
        if self._comp is None:      
            self._comp = CompositionClustering(self._input_dict)

    def _prepare_post_process(self):
        if self._post is None:
            self._post = DataPostprocess(self._input_dict)

    def _get_PCA_cumsum(self):
        self._prepare_comp()
        self._comp.get_PCA_cumsum(self._data.voxel_ratio_files[self.input.fileindex], 
            self._data.voxel_files[self.input.fileindex])

    def _get_bics_minimization(self):
        self._prepare_comp()
        self._comp.get_bics_minimization(self._data.voxel_ratio_files[self.input.fileindex], 
            self._data.voxel_files[self.input.fileindex])

    def _get_composition_clusters(self):
        self._prepare_comp()
        self._comp.get_composition_clusters(self._data.voxel_ratio_files[self.input.fileindex], 
            self._data.voxel_files[self.input.fileindex])
        self._composition_clusters_found = True

    def _get_dbscan_clustering(self):
        
        if not self._composition_clusters_found:
            self._get_composition_clusters()
        
        self._prepare_post_process()
        
        self._post.DBSCAN_clustering(self._comp.voxel_centroid_output_file, 
                        cluster_id = self.input.cluster_id,
                        plot=self.input.plot, plot3d=self.input.plot3d, save=False)

    def plot3d(self, **kwargs):
        if self._comp is None:
            raise RuntimeError("Run any composition calculation before to plot")
        return self._comp.plot3d(**kwargs)

    def analyse(self, analysis=["PCA_cumsum", "bics_minimization",
        "composition_clustering", "dbscan_clustering"], 
        fileindex=0, cluster_id=0,
        plot=False, plot3d=False):

        self.input.analysis = [x.lower() for x in analysis]
        self.input.fileindex=fileindex
        self.input.fileindex=fileindex
        self.input.plot=plot
        self.input.plot3d=plot3d            

    def run_static(self):
        
        self.status.running = True
        self._data = DataPreparation(self._input_dict)
        self._data.chunkify_apt_df()
        self._data.get_voxels()
        self._data.calculate_voxel_composition()

        if "pca_cumsum" in self.input.analysis:
            self._get_PCA_cumsum()

        if "bics_minimization" in self.input.analysis:
            self._get_bics_minimization()

        if "composition_clustering" in self.input.analysis:
            self._get_composition_clusters()

        if "dbscan_clustering" in self.input.analysis:
            self._get_dbscan_clustering()

        self.status.collect = True


    def collect_output(self):
        #self.collect_general_output()
        self.to_hdf()




