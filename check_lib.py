
try:
    import matplotlib
    print("Matplotlib found")
except ImportError:
    print("Matplotlib NOT found")

try:
    import pyqtgraph
    print("PyQtGraph found")
except ImportError:
    print("PyQtGraph NOT found")
