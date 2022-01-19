import os
import numpy as np

import hyperspy.api as hs

from pyiron_base._tests import TestWithCleanProject
import pyiron_experimental 


class TestHSLineProfiles(TestWithCleanProject):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        data = hs.load(os.path.join(cls.project.path, '../../notebooks/experiment.emd'))
        cls.signal = data[0]

    def setUp(self):
        self.job = self.project.create.job.HSLineProfiles('tem')

    def test_set_signal(self):
        signal = self.signal
        with self.subTest('No hs signal'):
            with self.assertRaises(ValueError):
                self.job.signal = None
        with self.subTest('intended use case'):
            self.job.signal = signal
            self.assertEqual(self.job.input.signal.hs_class_name, 'Signal2D')
            self.assertEqual(self.job.input.signal.axes, list(signal.axes_manager.as_dictionary().values()))
            self.assertTrue(np.array_equal(self.job.input.signal.data, signal.data))
            self.assertDictEqual(self.job.input.signal.metadata, signal.metadata.as_dictionary())
            self.assertDictEqual(self.job.input.signal.original_metadata, signal.original_metadata.as_dictionary())
        with self.subTest('already running'):
            self.job.status.running = True
            with self.assertRaises(RuntimeError):
                self.job.signal = signal

    def test_hs(self):
        data = self.job.hs.load(os.path.join(self.project.path, '../../notebooks/experiment.emd'))
        self.assertEqual(data[0], self.signal)

    def test_static_workflow(self):
        self.job.signal = self.signal
        self.job.input.x = [[0, 50], [50, 50]]
        self.job.input.y = [[10, 10], [0, 50]]
        self.job.run()
        self.assertEqual(len(self.job.output), 2)
        with self.subTest('Output line 0'):
            output = self.job.output[0]
            self.assertEqual(output['line'], 0)
            self.assertTrue(np.array_equal(output['x'], [0, 50]), msg=f"Expected {[0, 50]} but got {output['x']}.")
            self.assertTrue(np.array_equal(output['y'], [10, 10]), msg=f"Expected {[10, 10]} but got {output['y']}.")
            self.assertAlmostEqual(np.sum(output['data']), 1577323.2)
        with self.subTest('Output line 1'):
            output = self.job.output[1]
            self.assertEqual(output['line'], 1)
            self.assertTrue(np.array_equal(output['x'], [50, 50]), msg=f"Expected {[50, 50]} but got {output['x']}.")
            self.assertTrue(np.array_equal(output['y'], [0, 50]), msg=f"Expected {[0, 50]} but got {output['y']}.")
            self.assertAlmostEqual(np.sum(output['data']), 1509104.4)

    def test_interactive_workflow(self):
        self.job.signal = self.signal
        self.job._useblit = False

        fig = self.job.plot_signal()
        fig.show()
        self.job.add_line(x=[0, 50], y=[10, 10])
        self.job.plot_line_profiles()

        with self.subTest('Output line 0'):
            output = self.job.output[0]
            self.assertEqual(output['line'], 0)
            self.assertTrue(np.array_equal(output['x'], [0, 50]), msg=f"Expected {[0, 50]} but got {output['x']}.")
            self.assertTrue(np.array_equal(output['y'], [10, 10]), msg=f"Expected {[10, 10]} but got {output['y']}.")
            self.assertAlmostEqual(np.sum(output['data']), 1577323.2)

        self.job.add_line(x=[50, 50], y=[0, 50])
        self.job.plot_line_profiles()
        with self.subTest('Output line 1'):
            output = self.job.output[1]
            self.assertEqual(output['line'], 0)
            self.assertTrue(np.array_equal(output['x'], [0, 50]), msg=f"Expected {[0, 50]} but got {output['x']}.")
            self.assertTrue(np.array_equal(output['y'], [10, 10]), msg=f"Expected {[10, 10]} but got {output['y']}.")
            self.assertAlmostEqual(np.sum(output['data']), 1577323.2)
        with self.subTest('Output line 2'):
            output = self.job.output[2]
            self.assertEqual(output['line'], 1)
            self.assertTrue(np.array_equal(output['x'], [50, 50]), msg=f"Expected {[50, 50]} but got {output['x']}.")
            self.assertTrue(np.array_equal(output['y'], [0, 50]), msg=f"Expected {[0, 50]} but got {output['y']}.")
            self.assertAlmostEqual(np.sum(output['data']), 1509104.4)

    def test_load_static_workflow(self):
        self.test_static_workflow()
        job = self.project.load('tem')

        self.assertEqual(job.signal, self.signal)

        with self.subTest('Output line 0'):
            output = job.output[0]
            self.assertEqual(output['line'], 0)
            self.assertTrue(np.array_equal(output['x'], [0, 50]), msg=f"Expected {[0, 50]} but got {output['x']}.")
            self.assertTrue(np.array_equal(output['y'], [10, 10]), msg=f"Expected {[10, 10]} but got {output['y']}.")
            self.assertAlmostEqual(np.sum(output['data']), 1577323.2)
        with self.subTest('Output line 1'):
            output = job.output[1]
            self.assertEqual(output['line'], 1)
            self.assertTrue(np.array_equal(output['x'], [50, 50]), msg=f"Expected {[50, 50]} but got {output['x']}.")
            self.assertTrue(np.array_equal(output['y'], [0, 50]), msg=f"Expected {[0, 50]} but got {output['y']}.")
            self.assertAlmostEqual(np.sum(output['data']), 1509104.4)

    def test_load_interactive_workflow(self):
        self.test_interactive_workflow()
        job = self.project.load('tem')

        self.assertEqual(job.signal, self.signal)

        with self.subTest('Output line 0'):
            output = job.output[0]
            self.assertEqual(output['line'], 0)
            self.assertTrue(np.array_equal(output['x'], [0, 50]), msg=f"Expected {[0, 50]} but got {output['x']}.")
            self.assertTrue(np.array_equal(output['y'], [10, 10]), msg=f"Expected {[10, 10]} but got {output['y']}.")
            self.assertAlmostEqual(np.sum(output['data']), 1577323.2)
        with self.subTest('Output line 1'):
            output = job.output[1]
            self.assertEqual(output['line'], 0)
            self.assertTrue(np.array_equal(output['x'], [0, 50]), msg=f"Expected {[0, 50]} but got {output['x']}.")
            self.assertTrue(np.array_equal(output['y'], [10, 10]), msg=f"Expected {[10, 10]} but got {output['y']}.")
            self.assertAlmostEqual(np.sum(output['data']), 1577323.2)
        with self.subTest('Output line 2'):
            output = job.output[2]
            self.assertEqual(output['line'], 1)
            self.assertTrue(np.array_equal(output['x'], [50, 50]), msg=f"Expected {[50, 50]} but got {output['x']}.")
            self.assertTrue(np.array_equal(output['y'], [0, 50]), msg=f"Expected {[0, 50]} but got {output['y']}.")
            self.assertAlmostEqual(np.sum(output['data']), 1509104.4)
