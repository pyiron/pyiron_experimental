import resistance_mdi
from pyiron_base import Project

p = Project("./job_test/")
p.remove_jobs_silently()

job_measure = p.create_job(resistance_mdi.ResistanceGP, "job_gp")
print(job.input)

job.input.sample_file = "/home/markus/repos/pyiron_demonstrator/data/Co-Fe-La-Mn-O_coordinates_composition_resistance.csv"
print(job.input)

job_measure.run()
print(job.output)

job_postproc = p.create_job(mdi_suite.xrd_postproc, "job_postproc")
job_postproc.input.xrd_measurement = job_measure
job_postproc.run()
