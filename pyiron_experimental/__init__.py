from pyiron_base import Project
from pyiron_base.job.jobtype import JOB_CLASS_DICT


JOB_CLASS_DICT["pySTEMTEMMETAJob"] = "pyiron_experimental.pystemjob"
JOB_CLASS_DICT["TEMMETAJob"] = "pyiron_experimental.temmetajob"
JOB_CLASS_DICT["MatchSeries"] = "pyiron_experimental.matchseries"
