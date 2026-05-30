import unittest
from echo import Echo
from signals import EncoderVendor1, I_Encoder

class TestEcho(unittest.TestCase):
    def setUp(self):
        self.echo = Echo()

    def test_repeat(self):
        self.assertEqual(self.echo.repeat("hello"), "hello")
        self.assertEqual(self.echo.repeat("world"), "world")
        self.assertEqual(self.echo.repeat(""), "")

    def test_loudly(self):
        self.assertEqual(self.echo.loudly("hello"), "HELLO")
        self.assertEqual(self.echo.loudly("world"), "WORLD")
        self.assertEqual(self.echo.loudly(""), "")
   
class TestEncoder(unittest.TestCase):
    def setUp(self):
        self.encoder = EncoderVendor1(position=100, velocity=50)
 
    def test_position(self):
        self.assertEqual(self.encoder.position, 100)
 
    def test_velocity(self):
        self.assertEqual(self.encoder.velocity, 50)
 
    def test_read(self):
        self.assertTrue(self.encoder.read())
 
    def test_read_returns_bool(self):
        self.assertIsInstance(self.encoder.read(), bool)
 
    def test_distinct_values(self):
        # position and velocity are independent fields
        enc = EncoderVendor1(position=0, velocity=-50)
        self.assertEqual(enc.position, 0)
        self.assertEqual(enc.velocity, -50)
 
    def test_position_is_read_only(self):
        # property has no setter, so assignment should raise
        with self.assertRaises(AttributeError):
            self.encoder.position = 999
 
    def test_velocity_is_read_only(self):
        with self.assertRaises(AttributeError):
            self.encoder.velocity = 999
 
    def test_implements_interface(self):
        # Encoder honors the I_Encoder contract
        self.assertIsInstance(self.encoder, I_Encoder)
 
    def test_interface_cannot_be_instantiated(self):
        # bare ABC with unimplemented abstractmethods can't be constructed
        with self.assertRaises(TypeError):
            I_Encoder()

if __name__ == '__main__':
    unittest.main()
