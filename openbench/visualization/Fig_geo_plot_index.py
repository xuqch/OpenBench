import sys
import warnings
from matplotlib import colors
from matplotlib import cm
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np
import math
import os
import pandas as pd
import matplotlib
try:
    from openbench.util.Mod_Converttype import Convert_Type
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openbench.util.Mod_Converttype import Convert_Type
warnings.simplefilter(action='ignore', category=RuntimeWarning)

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
import cmaps
from .Fig_toolbox import get_index, convert_unit, get_colormap, tick_length

def make_geo_plot_index(file, method_name, main_nml, option):
    import numpy as np
    import xarray as xr
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
    from matplotlib import rcParams

    ds = xr.open_dataset(f"{file}")
    ds = Convert_Type.convert_nc(ds)
    data = ds[method_name]
    ilat = ds.lat.values
    ilon = ds.lon.values
    lon, lat = np.meshgrid(ilon, ilat)

    min_value, max_value = np.nanmin(data), np.nanmax(data)
    cmap, mticks, norm, bnd, extend = get_index(min_value, max_value, option['cmap'])
    if not option['vmin_max_on']:
        option['vmax'], option['vmin'] = mticks[-1], mticks[0]
    
    font = {'family': option['font']}
    matplotlib.rc('font', **font)

    params = {'backend': 'ps',
              'axes.labelsize': option['labelsize'],
              'grid.linewidth': 0.2,
              'font.size': option['labelsize'],
              'xtick.labelsize': option['xtick'],
              'xtick.direction': 'out',
              'ytick.labelsize': option['ytick'],
              'ytick.direction': 'out',
              'savefig.bbox': 'tight',
              'axes.unicode_minus': False,
              'text.usetex': False}
    rcParams.update(params)

    fig = plt.figure(figsize=(option['x_wise'], option['y_wise']))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    extent = (ilon[0], ilon[-1], ilat[0], ilat[-1])
    if ilat[0] - ilat[-1] < 0:
        origin = 'lower'
    else:
        origin = 'upper'

    if option['show_method'] == 'interpolate':
        cs = ax.contourf(lon, lat, data, levels=bnd, cmap=cmap, norm=norm, extend=extend)
    else:
        cs = ax.imshow(data, cmap=cmap, vmin=mticks[0], vmax=mticks[-1], extent=extent, origin=origin)

    for spine in ax.spines.values():
        spine.set_linewidth(option['line_width'])

    coastline = cfeature.NaturalEarthFeature(
        'physical', 'coastline', '110m', edgecolor='0.6', facecolor='none')
    rivers = cfeature.NaturalEarthFeature(
        'physical', 'rivers_lake_centerlines', '110m', edgecolor='0.6', facecolor='none')
    ax.add_feature(cfeature.LAND, facecolor='0.9')
    ax.add_feature(coastline, linewidth=0.6)
    ax.add_feature(cfeature.LAKES, alpha=1, facecolor='white', edgecolor='white')
    ax.add_feature(rivers, linewidth=0.5)
    ax.gridlines(draw_labels=False, linestyle=':', linewidth=0.5, color='grey', alpha=0.8,
        xlocs=np.arange(option['max_lon'], option['min_lon'], -60)[:0:-1],
        ylocs=np.arange(option['max_lat'], option['min_lat'], -30)[:0:-1])

    if not option['set_lat_lon']:
        ax.set_extent([main_nml['min_lon'], main_nml['max_lon'], main_nml['min_lat'],
                       main_nml['max_lat']], crs=ccrs.PlateCarree())
        ax.set_xticks(np.arange(main_nml['max_lon'], main_nml['min_lon'], -60)[:0:-1],
                      crs=ccrs.PlateCarree())
        ax.set_yticks(np.arange(main_nml['max_lat'], main_nml['min_lat'], -30)[:0:-1],
                      crs=ccrs.PlateCarree())
    else:
        ax.set_extent([option['min_lon'], option['max_lon'], option['min_lat'], option['max_lat']], crs=ccrs.PlateCarree())
        ax.set_xticks(np.arange(option['max_lon'], option['min_lon'], -60)[:0:-1], crs=ccrs.PlateCarree())
        ax.set_yticks(np.arange(option['max_lat'], option['min_lat'], -30)[:0:-1], crs=ccrs.PlateCarree())
    ax.tick_params(axis='x', color="#969696", width=1.5, length=4,which='major')  
    ax.tick_params(axis='y', color="#969696", width=1.5, length=4,which='major')
    ax.set_adjustable('datalim')
    ax.set_aspect('equal', adjustable='box')
    lon_formatter = LongitudeFormatter()
    lat_formatter = LatitudeFormatter()
    ax.xaxis.set_major_formatter(lon_formatter)
    ax.yaxis.set_major_formatter(lat_formatter)

    if not option['colorbar_position_set']:
        pos = ax.get_position()
        left, right, bottom, width, height = pos.x0, pos.x1, pos.y0, pos.width, pos.height
        if (option['min_lat']<-60) & (option['max_lat']>89) & (option['min_lon']<-179) & (option['max_lon']>179):
            if option['colorbar_position'] == 'horizontal':
                cbaxes = fig.add_axes([left + 0.03, bottom+ 0.14, 0.15, 0.02])
                ax.text(-130,-40,option['colorbar_label'],fontsize=16, weight='bold', ha='center' ,va='bottom')
            else:
                cbaxes = fig.add_axes([left + 0.015, bottom + 0.08, 0.02, height/3])
                ax.text(-160+7*tick_length(np.median(mticks)),-40,option['colorbar_label'],fontsize=16, weight='bold', ha='left' ,va='center')
        else:
            if option['colorbar_position'] == 'horizontal':
                if len(option['xticklabel']) == 0:
                    cbaxes = fig.add_axes([left + width / 8, bottom - 0.1, width/4*3, 0.03])
                else:
                    cbaxes = fig.add_axes([left + width / 8, bottom - 0.15, width/4*3, 0.03])
            else:
                cbaxes = fig.add_axes([right + 0.01, bottom, 0.015, height])
    else:
        cbaxes = fig.add_axes(
            [option["colorbar_left"], option["colorbar_bottom"], option["colorbar_width"], option["colorbar_height"]])

    cb = fig.colorbar(cs, cax=cbaxes, ticks=mticks, spacing='uniform', label=option['colorbar_label'], extend=extend,
                      orientation=option['colorbar_position'])
    cb.solids.set_edgecolor("face")

    file2 = file[:-3]
    plt.savefig(f'{file2}.{option["saving_format"]}', format=f'{option["saving_format"]}',
                dpi=option['dpi'])
    plt.close()
