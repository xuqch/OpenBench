import math

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib import rcParams
try:
    from openbench.util.Mod_Converttype import Convert_Type
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openbench.util.Mod_Converttype import Convert_Type


def make_LC_based_heat_map(file, selected_metrics, lb, option):
    selected_metrics = list(selected_metrics)
    # Convert the data to a DataFrame
    # read the data from the file using csv, remove the first row, then set the index to the first column
    df = pd.read_csv(file, sep=r'\s+', skiprows=1, header=0)
    df = Convert_Type.convert_Frame(df)
    df.set_index('FullName', inplace=True)
    # Select the desired metrics
    # selected_metrics = ['nBiasScore', 'nRMSEScore', 'nPhaseScore', 'nIavScore', 'nSpatialScore', 'overall_score']
    df_selected = df.loc[selected_metrics]

    shorter = {
        'PFT_groupby':
            {
                "bare_soil": "BS",
                "needleleaf_evergreen_temperate_tree": "NETT",
                "needleleaf_evergreen_boreal_tree": "NEBT",
                "needleleaf_deciduous_boreal_tree": "NDBT",
                "broadleaf_evergreen_tropical_tree": "BETT",
                "broadleaf_evergreen_temperate_tree": "BETT",
                "broadleaf_deciduous_tropical_tree": "BDTT",
                "broadleaf_deciduous_temperate_tree": "BDTT",
                "broadleaf_deciduous_boreal_tree": "BDBT",
                "broadleaf_evergreen_shrub": "BES",
                "broadleaf_deciduous_temperate_shrub": "BDTS",
                "broadleaf_deciduous_boreal_shrub": "BDBS",
                "c3_arctic_grass": "C3AG",
                "c3_non-arctic_grass": "C3NAG",
                "c4_grass": "C4G",
                "c3_crop": "C3C",
                "Overall": 'Overall'
            },
        'IGBP_groupby': {
            "evergreen_needleleaf_forest": 'ENF',
            "evergreen_broadleaf_forest": 'EBF',
            "deciduous_needleleaf_forest": 'DNF',
            "deciduous_broadleaf_forest": 'DBF',
            "mixed_forests": 'MF',
            "closed_shrubland": 'CSH',
            "open_shrublands": 'OSH',
            "woody_savannas": 'WSA',
            "savannas": 'SAV',
            "grasslands": 'GRA',
            "permanent_wetlands": 'WET',
            "croplands": 'CRO',
            "urban_and_built_up": 'URB',
            "cropland_natural_vegetation_mosaic": 'CVM',
            "snow_and_ice": 'SNO',
            "barren_or_sparsely_vegetated": 'BSV',
            "water_bodies": 'WAT',
            "Overall": 'Overall',
        }
    }

    font = {'family': 'DejaVu Sans'}
    # font = {'family': option['font']}
    matplotlib.rc('font', **font)
    params = {'backend': 'ps',
              'axes.linewidth': option['axes_linewidth'],
              'font.size': option['fontsize'],
              'xtick.labelsize': option['xtick'],
              'xtick.direction': 'out',
              'ytick.labelsize': option['ytick'],
              'grid.linewidth': 1,
              'ytick.direction': 'out',
              'savefig.bbox': 'tight',
              'axes.unicode_minus': False,
              'text.usetex': False}
    rcParams.update(params)

    if lb == 'score':
        # Create the heatmap using Matplotlib
        fig, ax = plt.subplots(figsize=(option['x_wise'], option['y_wise']))
        if option['vmin_max_on']:
            vmin, vmax = option['vmin'], option['vmax']
        else:
            vmin, vmax = 0, 1
        if not option['cmap']:
            option['cmap'] = 'coolwarm'
        im = ax.imshow(df_selected, cmap=option['cmap'], vmin=vmin, vmax=vmax)

        ax.set_yticks(range(len(df_selected.index)))
        ax.set_xticks(range(len(df_selected.columns)))
        ax.set_yticklabels([index.replace('_', ' ') for index in df_selected.index], rotation=option['y_rotation'],
                           ha=option['y_ha'])
        if option["x_ticklabel"] == 'Normal':
            ax.set_xticklabels([columns.replace('_', ' ').title() for columns in df_selected.columns],
                               rotation=option['x_rotation'],
                               ha=option['x_ha'])
        else:
            item = option['groupby']
            ax.set_xticklabels([shorter[item][column] for column in df_selected.columns], rotation=option['x_rotation'],
                               ha=option['x_ha'])

        ax.set_ylabel('Scores', fontsize=option['ytick'] + 1)
        ax.set_xlabel(option['xlabel'], fontsize=option['xtick'] + 1)

        if len(option['title']) == 0:
            option['title'] = f'Heatmap of {lb}'
        ax.set_title(option['title'], fontsize=option['title_size'])

        for i in range(len(df_selected.index)):
            for j in range(len(df_selected.columns)):
                ax.text(j, i, f'{df_selected.iloc[i, j]:{option["ticks_format"]}}', ha='center', va='center',
                        color='white' if df_selected.iloc[i, j] > 0.8 else 'black' or df_selected.iloc[i, j] < 0.2,
                        fontsize=option['fontsize'])

        pos = ax.get_position()  # .bounds
        left, right, bottom, width, height = pos.x0, pos.x1, pos.y0, pos.width, pos.height

        if not option['colorbar_position_set']:
            if option["colorbar_position"] == 'vertical':
                cbar_ax = fig.add_axes([right + 0.05, bottom, 0.03, height])  # right + 0.2
            else:
                xlabel = ax.xaxis.label
                xticks = ax.get_xticklabels()
                max_xtick_height = 0
                for xtick in xticks:
                    bbox = xtick.get_window_extent()  # 获取每个 xtick 的包围框
                    bbox_transformed = bbox.transformed(fig.transFigure.inverted())  # 将像素转换为图坐标
                    max_xtick_height = max(max_xtick_height, bbox_transformed.height)
                if xlabel is not None:
                    bbox = xlabel.get_window_extent()  # 获取每个 xtick 的包围框
                    bbox_transformed = bbox.transformed(fig.transFigure.inverted())  # 将像素转换为图坐标
                    x_height = bbox_transformed.height
                    cbar_ax = fig.add_axes([left + width / 6, bottom - max_xtick_height - x_height - 0.1, width / 3 * 2, 0.04])
                else:
                    cbar_ax = fig.add_axes([left + width / 6, bottom - max_xtick_height - 0.1, width / 3 * 2, 0.04])
        else:
            cbar_ax = fig.add_axes(option["colorbar_left"], option["colorbar_bottom"], option["colorbar_width"],
                                   option["colorbar_height"])
        cbar = fig.colorbar(im, cax=cbar_ax, label=option['colorbar_label'], orientation=option['colorbar_position'],
                            extend=option['extend'])
    elif len(df_selected.index) == 1 and lb != 'score':
        fig, ax = plt.subplots(figsize=(option['x_wise'], option['y_wise']))

        selected_item, sim_source, ref_source = option['item'][0], option['item'][1], option['item'][2]

        metric = df_selected.index[0]
        print(metric)
        import glob
        files = glob.glob(f'{option["path"]}{selected_item}_ref_{ref_source}_sim_{sim_source}_{metric}*.nc')
        datasets = [xr.open_dataset(file) for file in files]
        for t, ds in enumerate(datasets):
            datasets[t] = ds.expand_dims(dim={'time': [t]})  # 为每个文件添加一个新的'time'维度

        combined_dataset = xr.concat(datasets, dim='time')
        quantiles = combined_dataset.quantile([0.05, 0.2, 0.8, 0.95], dim=['time', 'lat', 'lon'])
        # consider 0.05 and 0.95 value as the max/min value
        custom_vmin_vmax = {}
        if not option["vmin_max_on"]:
            if metric in ['bias', 'percent_bias', 'rSD', 'PBIAS_HF', 'PBIAS_LF']:
                custom_vmin_vmax[metric] = [quantiles[metric][0].values, quantiles[metric][-1].values,
                                            quantiles[metric][2].values, quantiles[metric][1].values]
            elif metric in ['NSE', 'KGE', 'KGESS', 'correlation', 'kappa_coeff', 'rSpearman']:
                custom_vmin_vmax[metric] = [-1, 1, 0.8, -0.8]
            elif metric in ['LNSE', 'ubNSE', 'rNSE', 'wNSE', 'wsNSE']:
                custom_vmin_vmax[metric] = [quantiles[metric][0].values, 1, 0.8, quantiles[metric][1].values]
            elif metric in ['RMSE', 'CRMSD', 'MSE', 'ubRMSE', 'nRMSE', 'mean_absolute_error', 'ssq', 've',
                            'absolute_percent_bias']:
                custom_vmin_vmax[metric] = [-1, quantiles[metric][-1].values, quantiles[metric][2].values, -0.8]
            else:
                custom_vmin_vmax[metric] = [0, 1, 0.8, 0.2]
        else:
            custom_vmin_vmax[metric] = [option["vmin"], option["vmax"], 0.8, 0.2]

        if not option['cmap']:
            option['cmap'] = 'coolwarm'

        vmin, vmax = custom_vmin_vmax[metric][0], custom_vmin_vmax[metric][1]
        x1, x2 = custom_vmin_vmax[metric][2], custom_vmin_vmax[metric][3]
        im = ax.imshow(df_selected, cmap=option['cmap'], vmin=vmin, vmax=vmax)

        ax.set_yticks(range(len(df_selected.index)))
        ax.set_xticks(range(len(df_selected.columns)))
        ax.set_yticklabels([index.replace('_', ' ') for index in df_selected.index], rotation=option['y_rotation'],
                           ha=option['y_ha'])
        if option["x_ticklabel"] == 'Normal':
            ax.set_xticklabels([columns.replace('_', ' ').title() for columns in df_selected.columns],
                               rotation=option['x_rotation'],
                               ha=option['x_ha'])
        else:
            item = option['groupby']
            ax.set_xticklabels([shorter[item][column] for column in df_selected.columns], rotation=option['x_rotation'],
                               ha=option['x_ha'])

        ax.set_ylabel('Metrics', fontsize=option['ytick'] + 1)
        ax.set_xlabel(option['xlabel'], fontsize=option['xtick'] + 1)

        if len(option['title']) == 0:
            option['title'] = f'Heatmap of {lb}'
        ax.set_title(option['title'], fontsize=option['title_size'])

        for i in range(len(df_selected.index)):
            for j in range(len(df_selected.columns)):
                ax.text(j, i, f'{df_selected.iloc[i, j]:{option["ticks_format"]}}', ha='center', va='center',
                        color='white' if df_selected.iloc[i, j] > x1 else 'black' or df_selected.iloc[i, j] < x2,
                        fontsize=option['fontsize'])

        pos = ax.get_position()  # .bounds
        left, right, bottom, width, height = pos.x0, pos.x1, pos.y0, pos.width, pos.height

        if not option['colorbar_position_set']:
            if option["colorbar_position"] == 'vertical':
                cbar_ax = fig.add_axes([right + 0.05, bottom, 0.03, height])  # right + 0.2
            else:
                xlabel = ax.xaxis.label
                xticks = ax.get_xticklabels()
                max_xtick_height = 0
                for xtick in xticks:
                    bbox = xtick.get_window_extent()  # 获取每个 xtick 的包围框
                    bbox_transformed = bbox.transformed(fig.transFigure.inverted())  # 将像素转换为图坐标
                    max_xtick_height = max(max_xtick_height, bbox_transformed.height)
                if xlabel is not None:
                    bbox = xlabel.get_window_extent()  # 获取每个 xtick 的包围框
                    bbox_transformed = bbox.transformed(fig.transFigure.inverted())  # 将像素转换为图坐标
                    x_height = bbox_transformed.height
                    cbar_ax = fig.add_axes(
                        [left + width / 6, bottom - max_xtick_height - x_height - 0.1, width / 3 * 2, 0.04])
                else:
                    cbar_ax = fig.add_axes([left + width / 6, bottom - max_xtick_height - 0.1, width / 3 * 2, 0.04])
        else:
            cbar_ax = fig.add_axes(option["colorbar_left"], option["colorbar_bottom"], option["colorbar_width"],
                                   option["colorbar_height"])
        cbar = fig.colorbar(im, cax=cbar_ax, label=option['colorbar_label'], orientation=option['colorbar_position'],
                            extend=option['extend'])
    else:
        selected_item, sim_source, ref_source = option['item'][0], option['item'][1], option['item'][2]
        mfigsize = (len(shorter[option['groupby']]), len(df_selected.index))
        fig, axes = plt.subplots(nrows=len(df_selected.index), ncols=1, figsize=mfigsize, sharex=True)
        fig.text(-0.01, 0.5, 'Metrics', va='center', rotation='vertical', fontsize=option['ytick'] + 1)
        plt.subplots_adjust(hspace=0)
        # get the minimal and maximal value
        if not option['cmap']:
            option['cmap'] = 'coolwarm'
        custom_vmin_vmax = {}
        for i, (metric, row_data) in enumerate(df_selected.iterrows()):
            import glob
            files = glob.glob(f'{option["path"]}{selected_item}_ref_{ref_source}_sim_{sim_source}_{metric}*.nc')
            datasets = [xr.open_dataset(file) for file in files]
            for t, ds in enumerate(datasets):
                datasets[t] = ds.expand_dims(dim={'time': [t]})  # 为每个文件添加一个新的'time'维度

            combined_dataset = xr.concat(datasets, dim='time')
            quantiles = combined_dataset.quantile([0.05, 0.2, 0.8, 0.95], dim=['time', 'lat', 'lon'])
            # consider 0.05 and 0.95 value as the max/min value

            if not option["vmin_max_on"]:
                if metric in ['bias', 'percent_bias', 'rSD', 'PBIAS_HF', 'PBIAS_LF']:
                    custom_vmin_vmax[metric] = [quantiles[metric][0].values, quantiles[metric][-1].values,
                                                quantiles[metric][2].values, quantiles[metric][1].values]
                elif metric in ['NSE', 'KGE', 'KGESS', 'correlation', 'kappa_coeff', 'rSpearman']:
                    custom_vmin_vmax[metric] = [-1, 1, 0.8, -0.8]
                elif metric in ['LNSE', 'ubNSE', 'rNSE', 'wNSE', 'wsNSE']:
                    custom_vmin_vmax[metric] = [quantiles[metric][0].values, 1, 0.8, quantiles[metric][1].values]
                elif metric in ['RMSE', 'CRMSD', 'MSE', 'ubRMSE', 'nRMSE', 'mean_absolute_error', 'ssq', 've',
                                'absolute_percent_bias']:
                    custom_vmin_vmax[metric] = [-1, quantiles[metric][-1].values, quantiles[metric][2].values, -0.8]
                else:
                    custom_vmin_vmax[metric] = [0, 1, 0.8, 0.2]
            else:
                custom_vmin_vmax[metric] = [option["vmin"], option["vmax"], 0.8, 0.2]

        for i, (row_name, row_data) in enumerate(df_selected.iterrows()):
            vmin, vmax = custom_vmin_vmax[row_name][0], custom_vmin_vmax[row_name][1]
            x1, x2 = custom_vmin_vmax[row_name][2], custom_vmin_vmax[row_name][3]
            im = axes[i].imshow(row_data.values.reshape(1, -1), cmap=option['cmap'],
                                vmin=vmin, vmax=vmax)
            # Add numbers to each cell
            for j, value in enumerate(row_data):
                axes[i].text(j, 0, f'{df_selected.iloc[i, j]:{option["ticks_format"]}}', ha='center', va='center',
                             color='white' if df_selected.iloc[i, j] > x1 or df_selected.iloc[i, j] < x2 else 'black',
                             fontsize=option['fontsize'] - 1)

            pos = axes[i].get_position()  # .bounds
            left, right, bottom, width, height = pos.x0, pos.x1, pos.y0, pos.width, pos.height
            cbar_ax = fig.add_axes([right + 0.02, bottom + height / 2, width * 2 / len(shorter[option['groupby']]), height / 4])
            cbar = fig.colorbar(im, cax=cbar_ax, orientation='horizontal', extend=option['extend'])
            cbar.set_ticks([math.ceil(vmin), (vmin + vmax) / 2, math.floor(vmax)])
            cbar.set_ticklabels([f'{vmin:.1f}', f'{(vmin + vmax) / 2:.1f}', f'{vmax:.1f}'])
            cbar.ax.tick_params(labelsize=9)

            if i < len(df_selected.index) - 1:
                axes[i].get_xaxis().set_visible(False)

            if i == 0:
                axes[i].spines['bottom'].set_visible(False)
            elif 0 < i < len(df_selected.index) - 1:
                axes[i].spines['top'].set_visible(False)
                axes[i].spines['bottom'].set_visible(False)
            else:
                axes[i].spines['top'].set_visible(False)

            axes[i].set_yticks([0])
            axes[i].set_yticklabels([selected_metrics[i].replace('_', ' ')], rotation=option['y_rotation'], ha=option['y_ha'])

        # 设置 x 轴标签
        axes[-1].set_xticks(np.arange(len(df_selected.columns)))
        if option["x_ticklabel"] == 'Normal':
            axes[-1].set_xticklabels([columns.replace('_', ' ').title() for columns in df_selected.columns],
                                     rotation=option['x_rotation'],
                                     ha=option['x_ha'])
        else:
            item = option['groupby']
            axes[-1].set_xticklabels([shorter[item][column] for column in df_selected.columns], rotation=option['x_rotation'],
                                     ha=option['x_ha'])

        axes[-1].set_xlabel(option['xlabel'], fontsize=option['xtick'] + 1)
        axes[0].set_title(option['title'], fontsize=option['title_size'])

    file2 = file[:-4]
    plt.savefig(f'{file2}_heatmap.{option["saving_format"]}', format=f'{option["saving_format"]}', dpi=option['dpi'])
    # plt.show()


def make_CZ_based_heat_map(file, selected_metrics, lb, option):
    selected_metrics = list(selected_metrics)
    # Convert the data to a DataFrame
    # read the data from the file using csv, remove the first row, then set the index to the first column
    df = pd.read_csv(file, sep=r'\s+', skiprows=1, header=0)
    df = Convert_Type.convert_Frame(df)
    df.set_index('FullName', inplace=True)
    # Select the desired metrics
    df_selected = df.loc[selected_metrics]

    CZ_class_names = {
        1: "Af",
        2: "Am",
        3: "Aw",
        4: "BWh",
        5: "BWk",
        6: "BSh",
        7: "BSk",
        8: "Csa",
        9: "Csb",
        10: "Csc",
        11: "Cwa",
        12: "Cwb",
        13: "Cwc",
        14: "Cfa",
        15: "Cfb",
        16: "Cfc",
        17: "Dsa",
        18: "Dsb",
        19: "Dsc",
        20: "Dsd",
        21: "Dwa",
        22: "Dwb",
        23: "Dwc",
        24: "Dwd",
        25: "Dfa",
        26: "Dfb",
        27: "Dfc",
        28: "Dfd",
        29: "ET",
        30: "EF"
    }

    font = {'family': 'DejaVu Sans'}
    matplotlib.rc('font', **font)
    params = {'backend': 'ps',
              'axes.linewidth': option['axes_linewidth'],
              'font.size': option['fontsize'],
              'xtick.labelsize': option['xtick'],
              'xtick.direction': 'out',
              'ytick.labelsize': option['ytick'],
              'grid.linewidth': 1,
              'ytick.direction': 'out',
              'savefig.bbox': 'tight',
              'axes.unicode_minus': False,
              'text.usetex': False}
    rcParams.update(params)

    if lb == 'score':
        # Create the heatmap using Matplotlib
        fig, axes = plt.subplots(nrows=2, figsize=(option['x_wise'], option['y_wise']))
        if option['vmin_max_on']:
            vmin, vmax = option['vmin'], option['vmax']
        else:
            vmin, vmax = 0, 1
        if not option['cmap']:
            option['cmap'] = 'coolwarm'
        im1 = axes[0].imshow(df_selected.iloc[:,:16], cmap=option['cmap'], vmin=vmin, vmax=vmax)
        im2 = axes[1].imshow(df_selected.iloc[:, 16:], cmap=option['cmap'], vmin=vmin, vmax=vmax)

        axes[0].set_xticks(range(len(df_selected.columns[:16])))
        axes[0].set_xticklabels([columns.replace('_', ' ').title() for columns in df_selected.columns[:16]],
                           rotation=option['x_rotation'],
                           ha=option['x_ha'])
        for i in range(len(df_selected.index)):
            for j in range(len(df_selected.columns[:16])):
                axes[0].text(j, i, f'{df_selected.iloc[i, j]:{option["ticks_format"]}}', ha='center', va='center',
                          color='white' if df_selected.iloc[i, j] > 0.8 else 'black' or df_selected.iloc[i, j] < 0.2,
                          fontsize=option['fontsize'])

        axes[1].set_xticks(range(len(df_selected.columns[16:])))
        axes[1].set_xticklabels([columns.replace('_', ' ').title() for columns in df_selected.columns[16:]],
                           rotation=option['x_rotation'],
                           ha=option['x_ha'])
        for i in range(len(df_selected.index)):
            for j in range(16,16+len(df_selected.columns[16:])):
                axes[1].text(j-16, i, f'{df_selected.iloc[i, j]:{option["ticks_format"]}}', ha='center', va='center',
                          color='white' if df_selected.iloc[i, j] > 0.8 else 'black' or df_selected.iloc[i, j] < 0.2,
                          fontsize=option['fontsize'])
        if len(option['title']) == 0:
            option['title'] = f'Heatmap of {lb}'
        axes[0].set_title(option['title'], fontsize=option['title_size'])


        for ax in axes.flat:
            ax.set_yticks(range(len(df_selected.index)))
            ax.set_yticklabels([index.replace('_', ' ') for index in df_selected.index], rotation=option['y_rotation'],
                               ha=option['y_ha'])
            ax.set_ylabel('Scores', fontsize=option['ytick'] + 1)
            ax.set_xlabel(option['xlabel'], fontsize=option['xtick'] + 1)

        pos0 = axes[0].get_position()  # 第一行
        pos1 = axes[-1].get_position()  # 最后一行（这里就是第二行）
        left, right, bottom, width, height = pos1.x0, pos1.x1, pos1.y0, pos1.width, pos0.y1 - pos1.y0

        if not option['colorbar_position_set']:
            if option["colorbar_position"] == 'vertical':
                cbar_ax = fig.add_axes([right + 0.05, bottom, 0.03, height])  # right + 0.2
            else:
                xlabel = axes[1].xaxis.label
                xticks = axes[1].get_xticklabels()
                max_xtick_height = 0
                for xtick in xticks:
                    bbox = xtick.get_window_extent()  # 获取每个 xtick 的包围框
                    bbox_transformed = bbox.transformed(fig.transFigure.inverted())  # 将像素转换为图坐标
                    max_xtick_height = max(max_xtick_height, bbox_transformed.height)
                if xlabel is not None:
                    bbox = xlabel.get_window_extent()  # 获取每个 xtick 的包围框
                    bbox_transformed = bbox.transformed(fig.transFigure.inverted())  # 将像素转换为图坐标
                    x_height = bbox_transformed.height
                    cbar_ax = fig.add_axes([left + width / 6, bottom - max_xtick_height - x_height - 0.1, width / 3 * 2, 0.04])
                else:
                    cbar_ax = fig.add_axes([left + width / 6, bottom - max_xtick_height - 0.1, width / 3 * 2, 0.04])
        else:
            cbar_ax = fig.add_axes(option["colorbar_left"], option["colorbar_bottom"], option["colorbar_width"],
                                   option["colorbar_height"])
        cbar = fig.colorbar(im2, cax=cbar_ax, label=option['colorbar_label'], orientation=option['colorbar_position'],
                            extend=option['extend'])

    elif len(df_selected.index) == 1 and lb != 'score':
        fig, axes = plt.subplots(nrows=2, figsize=(option['x_wise'], option['y_wise']))
        selected_item, sim_source, ref_source = option['item'][0], option['item'][1], option['item'][2]
        metric = df_selected.index[0]
        import glob
        files = glob.glob(f'{option["path"]}{selected_item}_ref_{ref_source}_sim_{sim_source}_{metric}*.nc')
        datasets = [xr.open_dataset(file) for file in files]
        for t, ds in enumerate(datasets):
            datasets[t] = ds.expand_dims(dim={'time': [t]})  # 为每个文件添加一个新的'time'维度

        combined_dataset = xr.concat(datasets, dim='time')
        quantiles = combined_dataset.quantile([0.05, 0.2, 0.8, 0.95], dim=['time', 'lat', 'lon'])
        # consider 0.05 and 0.95 value as the max/min value
        custom_vmin_vmax = {}
        if not option["vmin_max_on"]:
            if metric in ['bias', 'percent_bias', 'rSD', 'PBIAS_HF', 'PBIAS_LF']:
                custom_vmin_vmax[metric] = [quantiles[metric][0].values, quantiles[metric][-1].values,
                                            quantiles[metric][2].values, quantiles[metric][1].values]
            elif metric in ['NSE', 'KGE', 'KGESS', 'correlation', 'kappa_coeff', 'rSpearman']:
                custom_vmin_vmax[metric] = [-1, 1, 0.8, -0.8]
            elif metric in ['LNSE', 'ubNSE', 'rNSE', 'wNSE', 'wsNSE']:
                custom_vmin_vmax[metric] = [quantiles[metric][0].values, 1, 0.8, quantiles[metric][1].values]
            elif metric in ['RMSE', 'CRMSD', 'MSE', 'ubRMSE', 'nRMSE', 'mean_absolute_error', 'ssq', 've',
                            'absolute_percent_bias']:
                custom_vmin_vmax[metric] = [-1, quantiles[metric][-1].values, quantiles[metric][2].values, -0.8]
            else:
                custom_vmin_vmax[metric] = [0, 1, 0.8, 0.2]
        else:
            custom_vmin_vmax[metric] = [option["vmin"], option["vmax"], 0.8, 0.2]

        if not option['cmap']:
            option['cmap'] = 'coolwarm'

        vmin, vmax = custom_vmin_vmax[metric][0], custom_vmin_vmax[metric][1]
        x1, x2 = custom_vmin_vmax[metric][2], custom_vmin_vmax[metric][3]

        im1 = axes[0].imshow(df_selected.iloc[:,:16], cmap=option['cmap'], vmin=vmin, vmax=vmax)
        im2 = axes[1].imshow(df_selected.iloc[:, 16:], cmap=option['cmap'], vmin=vmin, vmax=vmax)

        for ax in axes.flat:
            ax.set_yticks(range(len(df_selected.index)))
            ax.set_yticklabels([index.replace('_', ' ') for index in df_selected.index], rotation=option['y_rotation'],
                               ha=option['y_ha'])
            ax.set_ylabel('Scores', fontsize=option['ytick'] + 1)
            ax.set_xlabel(option['xlabel'], fontsize=option['xtick'] + 1)


        axes[0].set_xticks(range(len(df_selected.columns[:16])))
        axes[0].set_xticklabels([columns.replace('_', ' ').title() for columns in df_selected.columns[:16]],
                           rotation=option['x_rotation'],
                           ha=option['x_ha'])
        for i in range(len(df_selected.index)):
            for j in range(len(df_selected.columns[:16])):
                axes[0].text(j, i, f'{df_selected.iloc[i, j]:{option["ticks_format"]}}', ha='center', va='center',
                          color='white' if df_selected.iloc[i, j] > 0.8 else 'black' or df_selected.iloc[i, j] < 0.2,
                          fontsize=option['fontsize'])
        #
        axes[1].set_xticks(range(len(df_selected.columns[16:])))
        axes[1].set_xticklabels([columns.replace('_', ' ').title() for columns in df_selected.columns[16:]],
                           rotation=option['x_rotation'],
                           ha=option['x_ha'])
        for i in range(len(df_selected.index)):
            for j in range(16,16+len(df_selected.columns[16:])):
                axes[1].text(j-16, i, f'{df_selected.iloc[i, j]:{option["ticks_format"]}}', ha='center', va='center',
                          color='white' if df_selected.iloc[i, j] > 0.8 else 'black' or df_selected.iloc[i, j] < 0.2,
                          fontsize=option['fontsize'])
        if len(option['title']) == 0:
            option['title'] = f'Heatmap of {lb}'
        axes[0].set_title(option['title'], fontsize=option['title_size'])


        pos0 = axes[0].get_position()  # 第一行
        pos1 = axes[-1].get_position()  # 最后一行（这里就是第二行）
        left, right, bottom, width, height = pos1.x0, pos1.x1, pos1.y0, pos1.width, pos0.y1 - pos1.y0

        if not option['colorbar_position_set']:
            if option["colorbar_position"] == 'vertical':
                cbar_ax = fig.add_axes([right + 0.05, bottom, 0.03, height])  # right + 0.2
            else:
                xlabel = axes[1].xaxis.label
                xticks = axes[1].get_xticklabels()
                max_xtick_height = 0
                for xtick in xticks:
                    bbox = xtick.get_window_extent()  # 获取每个 xtick 的包围框
                    bbox_transformed = bbox.transformed(fig.transFigure.inverted())  # 将像素转换为图坐标
                    max_xtick_height = max(max_xtick_height, bbox_transformed.height)
                if xlabel is not None:
                    bbox = xlabel.get_window_extent()  # 获取每个 xtick 的包围框
                    bbox_transformed = bbox.transformed(fig.transFigure.inverted())  # 将像素转换为图坐标
                    x_height = bbox_transformed.height
                    cbar_ax = fig.add_axes(
                        [left + width / 6, bottom - max_xtick_height - x_height - 0.1, width / 3 * 2, 0.04])
                else:
                    cbar_ax = fig.add_axes([left + width / 6, bottom - max_xtick_height - 0.1, width / 3 * 2, 0.04])
        else:
            cbar_ax = fig.add_axes(option["colorbar_left"], option["colorbar_bottom"], option["colorbar_width"],
                                   option["colorbar_height"])
        cbar = fig.colorbar(im2, cax=cbar_ax, label=option['colorbar_label'], orientation=option['colorbar_position'],
                            extend=option['extend'])
    else:
        selected_item, sim_source, ref_source = option['item'][0], option['item'][1], option['item'][2]
        mfigsize = (15, len(df_selected.index)*2)

        from matplotlib.gridspec import GridSpec
        nrows_original = len(df_selected.index)
        nrows_total = 2 * nrows_original

        fig = plt.figure(figsize=mfigsize)
        gs = GridSpec(nrows_total + 1, 1)  # +1 是为了在两块之间添加间隔
        axes_part1 = []
        for i in range(nrows_original):
            if i == 0:
                ax = fig.add_subplot(gs[i])
            else:
                ax = fig.add_subplot(gs[i], sharex=axes_part1[0])
            axes_part1.append(ax)

        width_scale = 16/15

        axes_part2 = []
        for i in range(nrows_original):
            gs_pos = nrows_original + 1 + i  # +1 是为了跳过间隔行
            if i == 0:
                ax = fig.add_subplot(gs[gs_pos])
            else:
                ax = fig.add_subplot(gs[gs_pos], sharex=axes_part2[0])
            pos = ax.get_position()
            new_width = pos.width * width_scale
            ax.set_position([pos.x0, pos.y0, new_width, pos.height])
            axes_part2.append(ax)


        plt.subplots_adjust(hspace=0)  # 每部分内部无间隔
        fig.text(-0.01, 0.5, 'Metrics', va='center', rotation='vertical', fontsize=option['ytick'] + 1)

        # get the minimal and maximal value
        if not option['cmap']:
            option['cmap'] = 'coolwarm'

        custom_vmin_vmax = {}
        df_1= df_selected.iloc[:,:16]
        for i, (metric, row_data) in enumerate(df_1.iterrows()):
            import glob
            files = glob.glob(f'{option["path"]}{selected_item}_ref_{ref_source}_sim_{sim_source}_{metric}*.nc')
            datasets = [xr.open_dataset(file) for file in files]
            for t, ds in enumerate(datasets):
                datasets[t] = ds.expand_dims(dim={'time': [t]})  # 为每个文件添加一个新的'time'维度

            combined_dataset = xr.concat(datasets, dim='time')
            quantiles = combined_dataset.quantile([0.05, 0.2, 0.8, 0.95], dim=['time', 'lat', 'lon'])
            # consider 0.05 and 0.95 value as the max/min value

            if not option["vmin_max_on"]:
                if metric in ['bias', 'percent_bias', 'rSD', 'PBIAS_HF', 'PBIAS_LF']:
                    custom_vmin_vmax[metric] = [quantiles[metric][0].values, quantiles[metric][-1].values,
                                                quantiles[metric][2].values, quantiles[metric][1].values]
                elif metric in ['NSE', 'KGE', 'KGESS', 'correlation', 'kappa_coeff', 'rSpearman']:
                    custom_vmin_vmax[metric] = [-1, 1, 0.8, -0.8]
                elif metric in ['LNSE', 'ubNSE', 'rNSE', 'wNSE', 'wsNSE']:
                    custom_vmin_vmax[metric] = [quantiles[metric][0].values, 1, 0.8, quantiles[metric][1].values]
                elif metric in ['RMSE', 'CRMSD', 'MSE', 'ubRMSE', 'nRMSE', 'mean_absolute_error', 'ssq', 've',
                                'absolute_percent_bias']:
                    custom_vmin_vmax[metric] = [-1, quantiles[metric][-1].values, quantiles[metric][2].values, -0.8]
                else:
                    custom_vmin_vmax[metric] = [0, 1, 0.8, 0.2]
            else:
                custom_vmin_vmax[metric] = [option["vmin"], option["vmax"], 0.8, 0.2]

        for i, (row_name, row_data) in enumerate(df_1.iterrows()):
            vmin, vmax = custom_vmin_vmax[row_name][0], custom_vmin_vmax[row_name][1]
            x1, x2 = custom_vmin_vmax[row_name][2], custom_vmin_vmax[row_name][3]
            im = axes_part1[i].imshow(row_data.values.reshape(1, -1), cmap=option['cmap'],
                                vmin=vmin, vmax=vmax)
            for j, value in enumerate(row_data):
                axes_part1[i].text(j, 0, f'{df_1.iloc[i, j]:{option["ticks_format"]}}', ha='center', va='center',
                             color='white' if df_1.iloc[i, j] > x1 or df_1.iloc[i, j] < x2 else 'black',
                             fontsize=option['fontsize'] - 1)

            pos = axes_part1[i].get_position()  # .bounds
            left, right, bottom, width, height = pos.x0, pos.x1, pos.y0, pos.width, pos.height
            cbar_ax = fig.add_axes([right + 0.02, bottom + height / 2, width * 2 / len(df_1.columns), height / 4])
            cbar = fig.colorbar(im, cax=cbar_ax, orientation='horizontal', extend=option['extend'])
            cbar.set_ticks([math.ceil(vmin), (vmin + vmax) / 2, math.floor(vmax)])
            cbar.set_ticklabels([f'{vmin:.1f}', f'{(vmin + vmax) / 2:.1f}', f'{vmax:.1f}'])
            cbar.ax.tick_params(labelsize=9)

            if i < len(df_1.index) - 1:
                axes_part1[i].get_xaxis().set_visible(False)

            if i == 0:
                axes_part1[i].spines['bottom'].set_visible(False)
            elif 0 < i < len(df_1.index) - 1:
                axes_part1[i].spines['top'].set_visible(False)
                axes_part1[i].spines['bottom'].set_visible(False)
            else:
                axes_part1[i].spines['top'].set_visible(False)

            axes_part1[i].set_yticks([0])
            axes_part1[i].set_yticklabels([selected_metrics[i].replace('_', ' ')], rotation=option['y_rotation'], ha=option['y_ha'])

        # 设置 x 轴标签
        axes_part1[-1].set_xticks(np.arange(len(df_1.columns)))

        axes_part1[-1].set_xticklabels([columns.replace('_', ' ').title() for columns in df_1.columns],
                                 rotation=option['x_rotation'],
                                 ha=option['x_ha'])
        axes_part1[-1].set_xlabel(option['xlabel'], fontsize=option['xtick'] + 1)
        axes_part1[0].set_title(option['title'], fontsize=option['title_size'])


        df_2= df_selected.iloc[:,16:]
        for i, (metric, row_data) in enumerate(df_2.iterrows()):
            import glob
            files = glob.glob(f'{option["path"]}{selected_item}_ref_{ref_source}_sim_{sim_source}_{metric}*.nc')
            datasets = [xr.open_dataset(file) for file in files]
            for t, ds in enumerate(datasets):
                datasets[t] = ds.expand_dims(dim={'time': [t]})  # 为每个文件添加一个新的'time'维度

            combined_dataset = xr.concat(datasets, dim='time')
            quantiles = combined_dataset.quantile([0.05, 0.2, 0.8, 0.95], dim=['time', 'lat', 'lon'])
            # consider 0.05 and 0.95 value as the max/min value

            if not option["vmin_max_on"]:
                if metric in ['bias', 'percent_bias', 'rSD', 'PBIAS_HF', 'PBIAS_LF']:
                    custom_vmin_vmax[metric] = [quantiles[metric][0].values, quantiles[metric][-1].values,
                                                quantiles[metric][2].values, quantiles[metric][1].values]
                elif metric in ['NSE', 'KGE', 'KGESS', 'correlation', 'kappa_coeff', 'rSpearman']:
                    custom_vmin_vmax[metric] = [-1, 1, 0.8, -0.8]
                elif metric in ['LNSE', 'ubNSE', 'rNSE', 'wNSE', 'wsNSE']:
                    custom_vmin_vmax[metric] = [quantiles[metric][0].values, 1, 0.8, quantiles[metric][1].values]
                elif metric in ['RMSE', 'CRMSD', 'MSE', 'ubRMSE', 'nRMSE', 'mean_absolute_error', 'ssq', 've',
                                'absolute_percent_bias']:
                    custom_vmin_vmax[metric] = [-1, quantiles[metric][-1].values, quantiles[metric][2].values, -0.8]
                else:
                    custom_vmin_vmax[metric] = [0, 1, 0.8, 0.2]
            else:
                custom_vmin_vmax[metric] = [option["vmin"], option["vmax"], 0.8, 0.2]
        for i, (row_name, row_data) in enumerate(df_2.iterrows()):
            vmin, vmax = custom_vmin_vmax[row_name][0], custom_vmin_vmax[row_name][1]
            x1, x2 = custom_vmin_vmax[row_name][2], custom_vmin_vmax[row_name][3]
            im = axes_part2[i].imshow(row_data.values.reshape(1, -1), cmap=option['cmap'],
                                vmin=vmin, vmax=vmax)
            for j, value in enumerate(row_data):
                axes_part2[i].text(j, 0, f'{df_2.iloc[i, j]:{option["ticks_format"]}}', ha='center', va='center',
                             color='white' if df_2.iloc[i, j] > x1 or df_2.iloc[i, j] < x2 else 'black',
                             fontsize=option['fontsize'] - 1)

            pos = axes_part2[i].get_position()  # .bounds
            left, right, bottom, width, height = pos.x0, pos.x1, pos.y0, pos.width, pos.height
            cbar_ax = fig.add_axes([right + 0.02, bottom + height / 2, width * 2 / len(df_2.columns), height / 4])
            cbar = fig.colorbar(im, cax=cbar_ax, orientation='horizontal', extend=option['extend'])
            cbar.set_ticks([math.ceil(vmin), (vmin + vmax) / 2, math.floor(vmax)])
            cbar.set_ticklabels([f'{vmin:.1f}', f'{(vmin + vmax) / 2:.1f}', f'{vmax:.1f}'])
            cbar.ax.tick_params(labelsize=9)

            if i < len(df_2.index) - 1:
                axes_part2[i].get_xaxis().set_visible(False)

            if i == 0:
                axes_part2[i].spines['bottom'].set_visible(False)
            elif 0 < i < len(df_2.index) - 1:
                axes_part2[i].spines['top'].set_visible(False)
                axes_part2[i].spines['bottom'].set_visible(False)
            else:
                axes_part2[i].spines['top'].set_visible(False)

            axes_part2[i].set_yticks([0])
            axes_part2[i].set_yticklabels([selected_metrics[i].replace('_', ' ')], rotation=option['y_rotation'], ha=option['y_ha'])

        axes_part2[-1].set_xticks(np.arange(len(df_2.columns)))

        axes_part2[-1].set_xticklabels([columns.replace('_', ' ').title() for columns in df_2.columns],
                                 rotation=option['x_rotation'],
                                 ha=option['x_ha'])
        axes_part2[-1].set_xlabel(option['xlabel'], fontsize=option['xtick'] + 1)



    file2 = file[:-4]
    plt.savefig(f'{file2}_heatmap.{option["saving_format"]}', format=f'{option["saving_format"]}', dpi=option['dpi'])
