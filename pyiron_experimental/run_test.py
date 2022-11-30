import resistance_mdi
from pyiron_base import Project

p = Project("./job_test/")
p.remove_jobs_silently()

job_measure = p.create_job(resistance_mdi.ResistanceGP, "job_gp")
print(job_measure.input)

# define already-measured data for dummy device
job_measure.input.sample_file = "../notebooks/Ir-Pd-Pt-Rh-Ru_dataset.csv"

# Output raw data

# define the columns for elemental concentrations
job_measure.input.element_column_ids = [3,-1]
print(job_measure.input)

job_measure.run()

print("DEVICE, raw data = \n", job_measure.device.raw_df)



print(job_measure.output["measurement_indices"])

#job_postproc = p.create_job(mdi_suite.xrd_postproc, "job_postproc")
#job_postproc.input.xrd_measurement = job_measure
#job_postproc.run()

# Note: this here needs to be put into a notebook with visualization
