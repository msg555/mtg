import unittest


from mtg import can_cast, load_standard_cards


class CastTest(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.CARDS = load_standard_cards()

  def test_beacon_bolas(self):
    self.assertTrue(can_cast(
      self.CARDS["Nicol Bolas, Dragon-God"],
      [
        self.CARDS["Interplanar Beacon"],
        self.CARDS["Interplanar Beacon"],
        self.CARDS["Interplanar Beacon"],
        self.CARDS["Mountain"],
        self.CARDS["Island"],
        self.CARDS["Island"],
      ],
    ))
    self.assertFalse(can_cast(
      self.CARDS["Nicol Bolas, Dragon-God"],
      [
        self.CARDS["Interplanar Beacon"],
        self.CARDS["Interplanar Beacon"],
        self.CARDS["Interplanar Beacon"],
        self.CARDS["Mountain"],
        self.CARDS["Island"],
      ],
    ))
    self.assertTrue(can_cast(
      self.CARDS["Nicol Bolas, Dragon-God"],
      [
        self.CARDS["Interplanar Beacon"],
        self.CARDS["Interplanar Beacon"],
        self.CARDS["Interplanar Beacon"],
        self.CARDS["Blast Zone"],
        self.CARDS["Swamp"],
      ],
    ))


if __name__ == "__main__":
  unittest.main()
