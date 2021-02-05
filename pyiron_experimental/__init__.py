__version__ = "0.1"
__all__ = []

from pyiron_base import Project, JOB_CLASS_DICT


JOB_CLASS_DICT["pySTEMTEMMETAJob"] = "pyiron_experimental.pystemjob"
JOB_CLASS_DICT["TEMMETAJob"] = "pyiron_experimental.temmetajob"
JOB_CLASS_DICT["MatchSeries"] = "pyiron_experimental.matchseries"

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions
