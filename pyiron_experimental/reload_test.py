import resistance_mdi
from pyiron_base import Project

pr = Project("./job_test/")
pr.remove_jobs_silently()

job_name = "job_gp_reload"

job_measure = pr.create_job(resistance_mdi.ResistanceGP, job_name)
print(job_measure.input)

# define already-measured data for dummy device
job_measure.input.sample_file = "../notebooks/Ir-Pd-Pt-Rh-Ru_dataset.csv"

# Output raw data

# define the columns for elemental concentrations
job_measure.input.element_column_ids = [3,-1]
print(job_measure.input)

job_measure.run()

job_reload = pr.load(job_name)

#print("DEVICE, raw data = \n", job2.device.raw_df)



print(job_reload.output)

#job_postproc = p.create_job(mdi_suite.xrd_postproc, "job_postproc")
#job_postproc.input.xrd_measurement = job_measure
#job_postproc.run()

# Note: this here needs to be put into a notebook with visualization
