def test_math():
    assert 2 + 2 == 4  # 配線チェック

def test_imports():
    import pandas as pd
    import numpy as np
    import yaml
    import jaconv
    assert pd.__version__ and np.__version__ and yaml.__version__ and jaconv.__version__
