from pyiron_base._tests import TestWithCleanProject


class TestMDIResistance(TestWithCleanProject):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.data_file = "../notebooks/Ir-Pd-Pt-Rh-Ru_dataset.csv"
        cls.reference_measurement_indices = [
            5,
            157,
            338,
            177,
            188,
            334,
            74,
            278,
            296,
            10,
            325,
            234,
            89,
            0,
            219,
            292,
        ]

    def setUp(self):
        self.job = self.project.create.job.ResistanceGP("resistance_test")

    def test_static_workflow(self):
        self.job.input.sample_file = self.data_file
        self.job.input.element_column_ids = [3, -1]
        self.job.run()

        measurement_indices = self.job.output["measurement_indices"]

        for value, reference in zip(
            measurement_indices, self.reference_measurement_indices
        ):
            self.assertEqual(value, reference)

    def test_load_static_workflow(self):
        self.test_static_workflow()
        job_load = self.project.load("resistance_test")

        measurement_indices = job_load.output["measurement_indices"]

        for value, reference in zip(
            measurement_indices, self.reference_measurement_indices
        ):
            self.assertEqual(value, reference)
