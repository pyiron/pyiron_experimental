import os
import scanf
from pyiron_base import TemplateJob, GenericParameters


class MatchSeries(TemplateJob):
    def __init__(self, project, job_name):
        super().__init__(project, job_name) 
        self.input = MatchSeriesInput()
        self.executable = "matchSeries 2> output.log"

    def _copy_restart_files(self):
        # copy images to working directory - bad shortcut ! 
        for file in os.listdir('.'):
            if scanf.scanf(self.input["templateNamePattern"], s=file, collapseWhitespace=True):
                self._restart_file_list.append(file)
        super()._copy_restart_files()
        
    def write_input(self): 
        self.input.write_file( 
            file_name="matchSeries.par",
            cwd=self.working_directory
        )

    def collect_output(self):
        pass



class MatchSeriesInput(GenericParameters):
    def __init__(self, input_file_name=None, **qwargs):
        super(MatchSeriesInput, self).__init__(
            input_file_name=input_file_name, table_name="matchSeries_par", comment_char="#"
        )
        
    def load_default(self):
        file_content = """\
deformationModel 0
reduceDeformations 1
templateNamePattern testImg_%d_STEM.tif
templateNumOffset 0
templateNumStep 1
numTemplates 4
cropInput 0
cropStartX 742
cropStartY 984
dontResizeOrCropReference 0
preSmoothSigma 0
saveRefAndTempl 0
numExtraStages 2
saveDirectory results/
dontNormalizeInputImages 0
enhanceContrastSaturationPercentage 0.15
normalizeMinToZero 1
lambda 200
lambdaFactor 1
MaxGradientDescentSteps 100
UseComponentWiseTimestep 1
maxGDIterations 200
stopEpsilon 1e-6
startLevel 6
stopLevel 8
precisionLevel 8
refineStartLevel 7
refineStopLevel 8
checkboxWidth 8
resizeInput 0
resampleInsteadOfProlongateDeformation 1
dontAccumulateDeformation 0
reuseStage1Results 1
extraStagesLambdaFactor 0.1
useMedianAsNewTarget 1
calcInverseDeformation 0
skipStage1 0
saveNamedDeformedTemplates 1
saveNamedDeformedTemplatesUsingNearestNeighborInterpolation 1
saveNamedDeformedTemplatesExtendedWithMean 1
saveDeformedTemplates 1
saveNamedDeformedDMXTemplatesAsDMX 1
saveNamedDeformations 1
"""
        self.load_string(file_content)
