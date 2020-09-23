from Ska.engarchive import fetch
import matplotlib.pyplot as plt
plt.figure(figsize=(6, 4), dpi=75)
dat = fetch.HrcSsMsid('2SHEV1RT', '2002:200', '2002:250', stat='5min')
dat.plot()
plt.grid()
plt.tight_layout()