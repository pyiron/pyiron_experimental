import resistance_mdi
from pyiron import Project

p = Project("./job_test/")
p.remove_jobs_silently()

job = p.create_job(resistance_mdi.ResistanceGP, "job_gp")
print(job.input)

job.input.sample_file = "/home/markus/repos/pyiron_demonstrator/data/Co-Fe-La-Mn-O_coordinates_composition_resistance.csv"
print(job.input)

job.run()
print(job.output)
