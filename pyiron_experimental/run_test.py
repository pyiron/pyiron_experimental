import resistance_mdi
from pyiron_base import Project

p = Project("./job_test/")
p.remove_jobs_silently()

job_measure = p.create_job(resistance_mdi.ResistanceGP, "job_gp")
print(job_measure.input)

job_measure.input.sample_file = "/home/markus/repos/pyiron_demonstrator/data/Co-Fe-La-Mn-O_coordinates_composition_resistance.csv"

# define already-measured data for dummy device
job_measure.input.sample_file = "Ir-Pd-Pt-Rh-Ru_dataset.csv"

# define the columns for elemental concentrations
job_measure.input.element_column_ids = [3,-1]
print(job_measure.input)

job_measure.run()
print(job_measure.output)

#job_postproc = p.create_job(mdi_suite.xrd_postproc, "job_postproc")
#job_postproc.input.xrd_measurement = job_measure
#job_postproc.run()

# Note: this here needs to be put into a notebook with visualization
