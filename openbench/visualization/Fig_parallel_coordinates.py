import itertools
import sys
import logging
import matplotlib
import matplotlib.pylab as pylab
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import rcParams
# import seaborn as sns
from matplotlib.cbook import flatten
try:
    from openbench.util.Mod_Converttype import Convert_Type
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openbench.util.Mod_Converttype import Convert_Type

def make_scenarios_comparison_parallel_coordinates(file, basedir, evaluation_items, scores, metrics,
                                                   option):
    # ----------------------------------------------------------------------------------#
    #                                                                                  #
    #                                                                                  #
    #                               Start the main loop                                #
    #                                                                                  #
    #                                                                                  #
    # ----------------------------------------------------------------------------------#
    # Set figure size
    font = {'family': option['font']}
    matplotlib.rc('font', **font)

    params = {'backend': 'ps',
              'axes.linewidth': option['axes_linewidth'],
              'font.size': 15,
              'xtick.labelsize': option['xticksize'],
              'xtick.direction': 'out',
              'ytick.labelsize': option['yticksize'],
              'ytick.direction': 'out',
              'savefig.bbox': 'tight',
              'axes.unicode_minus': False,
              'text.usetex': False}
    rcParams.update(params)
    # Set figure size
    figsize = (option['x_wise'], option['y_wise'])

    # Read the data from the file
    df = pd.read_csv(file, sep=r'\s+', header=0)
    df = Convert_Type.convert_Frame(df)
    # -------第一种情况：只有一个reference，一个item，多个模型，多个score-------
    # Get unique `Item` values and store them in `evaluation_items`.
    evaluation_items = df['Item'].unique()
    # Get unique `Reference` values for each `Item` and store them in `item_references`.
    item_references = df.groupby('Item')['Reference'].unique()
    # Get unique `Simulation` values and store them in `sim_sources`.
    sim_sources = df['Simulation'].unique()
    # Specify the scores to be plotted

    # Iterate over each evaluation item
    option['situation'] = 1
    if not option['set_legend']:
        legend_bbox_to_anchor = (0.5, -0.15)
    else:
        legend_bbox_to_anchor = (option["bbox_to_anchor_x"], option["bbox_to_anchor_y"])
    for evaluation_item in evaluation_items:
        # Get the corresponding references for the current evaluation item
        references = item_references[evaluation_item]
        # Iterate over each reference
        for ref_source in references:
            # Select rows where 'Item' matches the evaluation item and 'Reference' matches the reference
            df_selected = df.loc[(df['Item'] == evaluation_item) & (df['Reference'] == ref_source)]

            # Get the model names
            model_names = df_selected['Simulation'].values

            # Iterate over each score
            # Select the columns with the names of the score
            data = df_selected[scores].values

            # Create a new figure
            try:
            # Create the parallel coordinate plot
                fig, ax = parallel_coordinate_plot(data, list(scores), model_names,
                                                   models_to_highlight=model_names,
                                                   models_to_highlight_by_line=option["models_to_highlight_by_line"],
                                                   models_to_highlight_markers_size=option["models_to_highlight_markers_size"],
                                                   debug=False,
                                                   figsize=figsize,
                                                   colormap=option['cmap'],
                                                   xtick_labelsize=option['xticksize'],
                                                   ytick_labelsize=option['yticksize'],
                                                   legend_off=option["legend_off"],
                                                   legend_ncol=option["legend_ncol"],
                                                   legend_bbox_to_anchor=legend_bbox_to_anchor,
                                                   legend_loc=option["legend_loc"],
                                                   legend_fontsize=option["fontsize"],
                                                   option=option,
                                                   )
                ax.set_ylabel(option['yticklabel'], fontsize=option['yticksize'] + 1)
                ax.set_xlabel(option['xticklabel'], fontsize=option['xticksize'] + 1)
                ax.set_title(option['title'], fontsize=option['title_size'])
                # Save the plot

                output_file_path = f"{basedir}/output/comparisons/Parallel_Coordinates/Parallel_Coordinates_Plot_scores_{evaluation_item}_{ref_source}.{option['saving_format']}"
                fig.savefig(output_file_path, format=f'{option["saving_format"]}', dpi=option['dpi'], bbox_inches='tight')
            except:
                logging.error(f"Error in {evaluation_item} - {ref_source}, Scores contains Na  (Removing)")

    # -------第二种情况：多个item，多个模型，一个score，每幅图一个score
    option['situation'] = 2
    if not option['set_legend']:
        legend_bbox_to_anchor = (0.5, -0.25)
    else:
        legend_bbox_to_anchor = (option["bbox_to_anchor_x"], option["bbox_to_anchor_y"])
    # Filter unique values for `Item` and `Reference` and store it in `filtered_df`.
    filtered_df = df.groupby("Item")[["Reference"]].agg(lambda x: list(x.unique())).reset_index()

    # Get unique `Item` values and store them in `unique_items`.
    unique_items = filtered_df['Item'].unique()

    # Get unique `Simulation` values and store them in `sim_sources`.
    sim_sources = df['Simulation'].unique()

    # Specify the scores to be plotted
    # scores = sco['nBiasScore', 'overall_score']

    # Generate all combinations of `Reference` values from `filtered_df`.
    all_combinations = list(itertools.product(*filtered_df['Reference']))

    # Iterate over each score
    for score in scores:
        # Iterate over each `item_combination` in the generated combinations.
        for item_combination in all_combinations:
            # Create a boolean mask to filter rows where `Item` and `Reference` match the current combination.
            mask = pd.Series(False, index=df.index)
            for i, item in enumerate(unique_items):
                mask |= (df['Item'] == item) & (df['Reference'] == item_combination[i])

            # Filter the DataFrame based on the boolean mask.
            filtered_df = df[mask]

            # Create a new figure
            plt.subplots(figsize=figsize)

            # Create an empty list to store the data for each simulation
            data_list = []
            model_names = []

            # Iterate over each simulation
            for sim_source in sim_sources:
                # Select rows where 'Simulation' matches the current simulation
                df_selected = filtered_df.loc[filtered_df['Simulation'] == sim_source]

                # Extract the score values for each item in the current simulation
                score_values = df_selected.set_index('Item')[score].reindex(unique_items).values.reshape(1, -1)
                data_list.append(score_values)
                model_names.append(sim_source)

            # Concatenate the data from all simulations
            data = np.concatenate(data_list, axis=0)

            # Create the parallel coordinate plot
            try:
                fig, ax = parallel_coordinate_plot(data, unique_items, model_names,
                                                   models_to_highlight=model_names,
                                                   models_to_highlight_by_line=option["models_to_highlight_by_line"],
                                                   models_to_highlight_markers_size=option["models_to_highlight_markers_size"],
                                                   debug=False,
                                                   figsize=figsize,
                                                   colormap=option['cmap'],
                                                   xtick_labelsize=option['xticksize'],
                                                   ytick_labelsize=option['yticksize'],
                                                   legend_off=option["legend_off"],
                                                   legend_ncol=option["legend_ncol"],
                                                   legend_bbox_to_anchor=legend_bbox_to_anchor,
                                                   legend_loc=option["legend_loc"],
                                                   legend_fontsize=option["fontsize"],
                                                   option=option, )

                # Set the title of the plot
                title = option['title']
                ypad = 0
                if option['title'] == '':
                    title = f"Parallel Coordinates Plot - {score.replace('_', ' ')} \n References: {', '.join(item_combination).replace('_', ' ')}"
                    ypad = 10
                ax.set_title(title, fontsize=option['title_size'], pad=ypad)
                ax.set_ylabel(option['yticklabel'], fontsize=option['yticksize'] + 1)
                ax.set_xlabel(option['xticklabel'], fontsize=option['xticksize'] + 1)
                # Save the plot
                output_file_path = f"{basedir}/output/comparisons/Parallel_Coordinates/Parallel_Coordinates_Plot_{score}_{'_'.join(item_combination)}.{option['saving_format']}"
                fig.savefig(output_file_path, format=f'{option["saving_format"]}', dpi=option['dpi'], bbox_inches='tight')
            except:
                logging.error(f"Error in {score} - {item_combination} ")
    # ------------in the end of the function----------------

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # interate over each metric item
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Read the data from the file
    option['situation'] = 1
    if not option['set_legend']:
        legend_bbox_to_anchor = (0.5, -0.15)
    else:
        legend_bbox_to_anchor = (option["bbox_to_anchor_x"], option["bbox_to_anchor_y"])
    df = pd.read_csv(file, sep=r'\s+', header=0)
    df = Convert_Type.convert_Frame(df)
    # -------第一种情况：只有一个reference，一个item，多个模型，多个score-------
    # Get unique `Item` values and store them in `evaluation_items`.
    evaluation_items = df['Item'].unique()
    # Get unique `Reference` values for each `Item` and store them in `item_references`.
    item_references = df.groupby('Item')['Reference'].unique()
    # Get unique `Simulation` values and store them in `sim_sources`.
    sim_sources = df['Simulation'].unique()
    # Specify the scores to be plotted

    # Iterate over each evaluation item
    for evaluation_item in evaluation_items:
        # Get the corresponding references for the current evaluation item
        references = item_references[evaluation_item]
        # Iterate over each reference
        for ref_source in references:
            # Select rows where 'Item' matches the evaluation item and 'Reference' matches the reference
            df_selected = df.loc[(df['Item'] == evaluation_item) & (df['Reference'] == ref_source)]

            # Get the model names
            model_names = df_selected['Simulation'].values

            # Iterate over each score
            # Select the columns with the names of the score
            data = df_selected[metrics].values
            try:
                plt.subplots(figsize=figsize)

                # # Create the parallel coordinate plot
                fig, ax = parallel_coordinate_plot(data, list(metrics), model_names,
                                                   models_to_highlight=model_names,
                                                   models_to_highlight_by_line=option["models_to_highlight_by_line"],
                                                   models_to_highlight_markers_size=option["models_to_highlight_markers_size"],
                                                   debug=False,
                                                   figsize=figsize,
                                                   colormap=option['cmap'],
                                                   xtick_labelsize=option['xticksize'],
                                                   ytick_labelsize=option['yticksize'],
                                                   legend_off=option["legend_off"],
                                                   legend_ncol=option["legend_ncol"],
                                                   legend_bbox_to_anchor=legend_bbox_to_anchor,
                                                   legend_loc=option["legend_loc"],
                                                   legend_fontsize=option["fontsize"],
                                                   option=option, )

                # Save the plot
                ax.set_ylabel(option['yticklabel'], fontsize=option['yticksize'] + 1)
                ax.set_xlabel(option['xticklabel'], fontsize=option['xticksize'] + 1)
                ax.set_title(option['title'], fontsize=option['title_size'])

                output_file_path = f"{basedir}/output/comparisons/Parallel_Coordinates/Parallel_Coordinates_Plot_metrics_{evaluation_item}_{ref_source}.{option['saving_format']}"
                fig.savefig(output_file_path, format=f'{option["saving_format"]}', dpi=option['dpi'], bbox_inches='tight')
            except:
                logging.error(f"Error in {evaluation_item} - {ref_source}, metrics contains Nan (Removing) ")

    option['situation'] = 2
    if not option['set_legend']:
        legend_bbox_to_anchor = (0.5, -0.25)
    else:
        legend_bbox_to_anchor = (option["bbox_to_anchor_x"], option["bbox_to_anchor_y"])
    # -------第二种情况：多个item，多个模型，一个score，每幅图一个score
    df = pd.read_csv(file, sep=r'\s+', header=0)
    df = Convert_Type.convert_Frame(df)

    # Filter unique values for `Item` and `Reference` and store it in `filtered_df`.
    filtered_df = df.groupby("Item")[["Reference"]].agg(lambda x: list(x.unique())).reset_index()

    # Get unique `Item` values and store them in `unique_items`.
    unique_items = filtered_df['Item'].unique()

    # Get unique `Simulation` values and store them in `sim_sources`.
    sim_sources = df['Simulation'].unique()

    # Specify the scores to be plotted
    # scores = ['nBiasScore', 'overall_score']

    # Generate all combinations of `Reference` values from `filtered_df`.
    all_combinations = list(itertools.product(*filtered_df['Reference']))

    # Iterate over each metric
    for metric in metrics:
        # Iterate over each `item_combination` in the generated combinations.
        for item_combination in all_combinations:
            # Create a boolean mask to filter rows where `Item` and `Reference` match the current combination.
            mask = pd.Series(False, index=df.index)
            for i, item in enumerate(unique_items):
                mask |= (df['Item'] == item) & (df['Reference'] == item_combination[i])

            # Filter the DataFrame based on the boolean mask.
            filtered_df = df[mask]

            # Create a new figure
            plt.subplots(figsize=figsize)

            # Create an empty list to store the data for each simulation
            data_list = []
            model_names = []

            # Iterate over each simulation
            for sim_source in sim_sources:
                # Select rows where 'Simulation' matches the current simulation
                df_selected = filtered_df.loc[filtered_df['Simulation'] == sim_source]

                # Extract the score values for each item in the current simulation
                metric_values = df_selected.set_index('Item')[metric].reindex(unique_items).values.reshape(1, -1)
                data_list.append(metric_values)
                model_names.append(sim_source)

            # Concatenate the data from all simulations
            data = np.concatenate(data_list, axis=0)
            try:
                # Create the parallel coordinate plot
                fig, ax = parallel_coordinate_plot(data, unique_items, model_names,
                                                   models_to_highlight=model_names,
                                                   models_to_highlight_by_line=option["models_to_highlight_by_line"],
                                                   models_to_highlight_markers_size=option["models_to_highlight_markers_size"],
                                                   debug=False,
                                                   figsize=figsize,
                                                   colormap=option['cmap'],
                                                   xtick_labelsize=option['xticksize'],
                                                   ytick_labelsize=option['yticksize'],
                                                   legend_off=option["legend_off"],
                                                   legend_ncol=option["legend_ncol"],
                                                   legend_bbox_to_anchor=legend_bbox_to_anchor,
                                                   legend_loc=option["legend_loc"],
                                                   legend_fontsize=option["fontsize"],
                                                   option=option,
                                                   )

                # Set the title of the plot
                title = option['title']
                ypad = 0
                if option['title'] == '':
                    title = f"Parallel Coordinates Plot - {metric.replace('_', ' ')} \n References: {', '.join(item_combination).replace('_', ' ')}"
                    ypad = 10
                ax.set_title(title, fontsize=option['title_size'], pad=ypad)
                ax.set_ylabel(option['yticklabel'], fontsize=option['yticksize'] + 1)
                ax.set_xlabel(option['xticklabel'], fontsize=option['xticksize'] + 1)
                # Save the plot
                output_file_path = f"{basedir}/output/comparisons/Parallel_Coordinates/Parallel_Coordinates_Plot_{metric}_{'_'.join(item_combination)}.{option['saving_format']}"
                fig.savefig(output_file_path, format=f'{option["saving_format"]}', dpi=option['dpi'], bbox_inches='tight')
            except:
                logging.error(f"Error in {metric} - {item_combination} -4")

def _quick_qc(data, model_names, metric_names, model_names2=None):
    # Quick initial QC
    if data.shape[0] != len(model_names):
        sys.exit(
            "Error: data.shape[0], "
            + str(data.shape[0])
            + ", mismatch to len(model_names), "
            + str(len(model_names))
        )
    if data.shape[1] != len(metric_names):
        sys.exit(
            "Error: data.shape[1], "
            + str(data.shape[1])
            + ", mismatch to len(metric_names), "
            + str(len(metric_names))
        )
    if model_names2 is not None:
        # Check: model_names2 should be a subset of model_names
        for model in model_names2:
            if model not in model_names:
                sys.exit(
                    "Error: model_names2 should be a subset of model_names, but "
                    + model
                    + " is not in model_names"
                )
    # print("Passed a quick QC")


def _data_transform(
        data,
        metric_names,
        model_names,
        model_names2=None,
        group1_name="group1",
        group2_name="group2",
        vertical_center=None,
        ymax=None,
        ymin=None,
):
    # Data to plot
    ys = data  # stacked y-axis values
    N = ys.shape[1]  # number of vertical axis (i.e., =len(metric_names))

    if ymax is None:
        ymaxs = np.nanmax(ys, axis=0)  # maximum (ignore nan value)
    else:
        try:
            if isinstance(ymax, str) and ymax == "percentile":
                ymaxs = np.nanpercentile(ys, 95, axis=0)
            else:
                ymaxs = np.repeat(ymax, N)
        except ValueError:
            print(f"Invalid input for ymax: {ymax}")

    if ymin is None:
        ymins = np.nanmin(ys, axis=0)  # minimum (ignore nan value)
    else:
        try:
            if isinstance(ymin, str) and ymin == "percentile":
                ymins = np.nanpercentile(ys, 5, axis=0)
            else:
                ymins = np.repeat(ymin, N)
        except ValueError:
            print(f"Invalid input for ymin: {ymin}")

    ymeds = np.nanmedian(ys, axis=0)  # median
    ymean = np.nanmean(ys, axis=0)  # mean

    if vertical_center is not None:
        if vertical_center == "median":
            ymids = ymeds
        elif vertical_center == "mean":
            ymids = ymean
        elif isinstance(vertical_center, float) or isinstance(vertical_center, int):
            ymids = np.repeat(vertical_center, N)
        else:
            raise ValueError(f"vertical center {vertical_center} unknown.")

        for i in range(0, N):
            distance_from_middle = max(
                abs(ymaxs[i] - ymids[i]), abs(ymids[i] - ymins[i])
            )
            ymaxs[i] = ymids[i] + distance_from_middle
            ymins[i] = ymids[i] - distance_from_middle

    dys = ymaxs - ymins
    if ymin is None:
        ymins -= dys * 0.05  # add 5% padding below and above
    if ymax is None:
        ymaxs += dys * 0.05
    dys = ymaxs - ymins

    # Handle the case when ymins and ymaxs are the same for a particular axis
    zero_range_indices = np.where(dys == 0)[0]
    if len(zero_range_indices) > 0:
        for idx in zero_range_indices:
            if ymins[idx] == 0:
                ymaxs[idx] = 1
            else:
                ymins[idx] -= np.abs(ymins[idx]) * 0.05
                ymaxs[idx] += np.abs(ymaxs[idx]) * 0.05
        dys = ymaxs - ymins

    # Transform all data to be compatible with the main axis
    zs = np.zeros_like(ys)
    zs[:, 0] = ys[:, 0]
    zs[:, 1:] = (ys[:, 1:] - ymins[1:]) / dys[1:] * dys[0] + ymins[0]

    if vertical_center is not None:
        zs_middle = (ymids[:] - ymins[:]) / dys[:] * dys[0] + ymins[0]
    else:
        zs_middle = (ymaxs[:] - ymins[:]) / 2 / dys[:] * dys[0] + ymins[0]

    if model_names2 is not None:
        print("Models in the second group:", model_names2)

    # Pandas dataframe for seaborn plotting
    df_stacked = _to_pd_dataframe(
        data,
        metric_names,
        model_names,
        model_names2=model_names2,
        group1_name=group1_name,
        group2_name=group2_name,
    )
    df2_stacked = _to_pd_dataframe(
        zs,
        metric_names,
        model_names,
        model_names2=model_names2,
        group1_name=group1_name,
        group2_name=group2_name,
    )

    return zs, zs_middle, N, ymins, ymaxs, df_stacked, df2_stacked


def _to_pd_dataframe(
        data,
        metric_names,
        model_names,
        model_names2=None,
        group1_name="group1",
        group2_name="group2",
):
    # Pandas dataframe for seaborn plotting
    df = pd.DataFrame(data, columns=metric_names, index=model_names)
    # Stack
    # df_stacked = df.stack(dropna=False).reset_index()
    # df_stacked = df.stack(dropna=False, future_stack=True).reset_index()
    df_stacked = df.stack(future_stack=True).reset_index()
    df_stacked = df_stacked.rename(
        columns={"level_0": "Model", "level_1": "Metric", 0: "value"}
    )
    df_stacked = df_stacked.assign(group=group1_name)
    if model_names2 is not None:
        for model2 in model_names2:
            df_stacked["group"] = np.where(
                (df_stacked.Model == model2), group2_name, df_stacked.group
            )
    return df_stacked


def parallel_coordinate_plot(
        data,
        metric_names,
        model_names,
        models_to_highlight=list(),
        models_to_highlight_by_line=True,
        models_to_highlight_colors=None,
        models_to_highlight_labels=None,
        models_to_highlight_markers=["s", "o", "^", "*"],
        models_to_highlight_markers_size=22,
        fig=None,
        ax=None,
        figsize=(15, 5),
        show_boxplot=False,
        show_violin=False,
        violin_colors=("lightgrey", "pink"),
        violin_label=None,
        title=None,
        identify_all_models=True,
        xtick_labelsize=None,
        ytick_labelsize=None,
        colormap="viridis",
        num_color=20,
        legend_off=False,
        legend_ncol=6,
        legend_bbox_to_anchor=(0.5, -0.14),
        legend_loc="upper center",
        legend_fontsize=10,
        logo_rect=None,
        logo_off=False,
        model_names2=None,
        group1_name="group1",
        group2_name="group2",
        comparing_models=None,
        fill_between_lines=False,
        fill_between_lines_colors=("red", "green"),
        arrow_between_lines=False,
        arrow_between_lines_colors=("red", "green"),
        arrow_alpha=1,
        arrow_width=0.05,
        arrow_linewidth=0,
        arrow_head_width=0.15,
        arrow_head_length=0.15,
        vertical_center=None,
        vertical_center_line=False,
        vertical_center_line_label=None,
        ymax=None,
        ymin=None,
        debug=False,
        option={},
):
    """
    Parameters
    ----------
    - `data`: 2-d numpy array for metrics
    - `metric_names`: list, names of metrics for individual vertical axes (axis=1)
    - `model_names`: list, name of models for markers/lines (axis=0)
    - `models_to_highlight`: list, default=None, List of models to highlight as lines or marker
    - `models_to_highlight_by_line`: bool, default=True, highlight as lines. If False, as marker
    - `models_to_highlight_colors`: list, default=None, List of colors for models to highlight as lines
    - `models_to_highlight_labels`: list, default=None, List of string labels for models to highlight as lines
    - `models_to_highlight_markers`: list, matplotlib markers for models to highlight if as marker
    - `models_to_highlight_markers_size`: float, size of matplotlib markers for models to highlight if as marker
    - `fig`: `matplotlib.figure` instance to which the parallel coordinate plot is plotted.
             If not provided, use current axes or create a new one.  Optional.
    - `ax`: `matplotlib.axes.Axes` instance to which the parallel coordinate plot is plotted.
             If not provided, use current axes or create a new one.  Optional.
    - `figsize`: tuple (two numbers), default=(15,5), image size
    - `show_boxplot`: bool, default=False, show box and wiskers plot
    - `show_violin`: bool, default=False, show violin plot
    - `violin_colors`: tuple or list containing two strings for colors of violin. Default=("lightgrey", "pink")
    - `violin_label`: string to label the violin plot, when violin plot is not splited. Default is None.
    - `title`: string, default=None, plot title
    - `identify_all_models`: bool, default=True. Show and identify all models using markers
    - `xtick_labelsize`: number, fontsize for x-axis tick labels (optional)
    - `ytick_labelsize`: number, fontsize for x-axis tick labels (optional)
    - `colormap`: string, default='viridis', matplotlib colormap
    - `num_color`: integer, default=20, how many color to use.
    - `legend_off`: bool, default=False, turn off legend
    - `legend_ncol`: integer, default=6, number of columns for legend text
    - `legend_bbox_to_anchor`: tuple, defulat=(0.5, -0.14), set legend box location
    - `legend_loc`: string, default="upper center", set legend box location
    - `legend_fontsize`: float, default=8, legend font size
    - `logo_rect`: sequence of float. The dimensions [left, bottom, width, height] of the new Axes.
                All quantities are in fractions of figure width and height.  Optional.
    - `logo_off`: bool, default=False, turn off PMP logo
    - `model_names2`: list of string, should be a subset of `model_names`.  If given, violin plot will be split into 2 groups. Optional.
    - `group1_name`: string, needed for violin plot legend if splited to two groups, for the 1st group. Default is 'group1'.
    - `group2_name`: string, needed for violin plot legend if splited to two groups, for the 2nd group. Default is 'group2'.
    - `comparing_models`: tuple or list containing two strings for models to compare with colors filled between the two lines.
    - `fill_between_lines`: bool, default=False, fill color between lines for models in comparing_models
    - `fill_between_lines_colors`: tuple or list containing two strings of colors for filled between the two lines. Default=('red', 'green')
    - `arrow_between_lines`: bool, default=False, place arrows between two lines for models in comparing_models
    - `arrow_between_lines_colors`: tuple or list containing two strings of colors for arrow between the two lines. Default=('red', 'green')
    - `arrow_alpha`: float, default=1, transparency of arrow (faction between 0 to 1)
    - `arrow_width`: float, default is 0.05, width of arrow
    - `arrow_linewidth`: float, default is 0, width of arrow edge line
    - `arrow_head_width`: float, default is 0.15, widht of arrow head
    - `arrow_head_length`: float, default is 0.15, length of arrow head
    - `vertical_center`: string ("median", "mean")/float/integer, default=None, adjust range of vertical axis to set center of vertical axis as median, mean, or given number
    - `vertical_center_line`: bool, default=False, show median as line
    - `vertical_center_line_label`: str, default=None, label in legend for the horizontal vertical center line. If not given, it will be automatically assigned. It can be turned off by "off"
    - `ymax`: int or float or string ('percentile'), default=None, specify value of vertical axis top. If percentile, 95th percentile or extended for top
    - `ymin`: int or float or string ('percentile'), default=None, specify value of vertical axis bottom. If percentile, 5th percentile or extended for bottom

    Return
    ------
    - `fig`: matplotlib component for figure
    - `ax`: matplotlib component for axis

    Author: Jiwoo Lee @ LLNL (2021. 7)
    Update history:
    2021-07 Plotting code created. Inspired by https://stackoverflow.com/questions/8230638/parallel-coordinates-plot-in-matplotlib
    2022-09 violin plots added
    2023-03 median centered option added
    2023-04 vertical center option diversified (median, mean, or given number)
    2024-03 parameter added for violin plot label
    2024-04 parameters added for arrow and option added for ymax/ymin setting
    """
    params = {
        "legend.fontsize": "large",
        "axes.labelsize": "x-large",
        "axes.titlesize": "x-large",
        "xtick.labelsize": "x-large",
        "ytick.labelsize": "x-large",
    }
    pylab.rcParams.update(params)

    # Quick initial QC
    _quick_qc(data, model_names, metric_names, model_names2=model_names2)

    # Transform data for plotting
    zs, zs_middle, N, ymins, ymaxs, df_stacked, df2_stacked = _data_transform(
        data,
        metric_names,
        model_names,
        model_names2=model_names2,
        group1_name=group1_name,
        group2_name=group2_name,
        vertical_center=vertical_center,
        ymax=ymax,
        ymin=ymin,
    )

    if debug:
        print("ymins:", ymins)
        print("ymaxs:", ymaxs)

    # Prepare plot
    if N > 20:
        if xtick_labelsize is None:
            xtick_labelsize = "large"
        if ytick_labelsize is None:
            ytick_labelsize = "large"
    else:
        if xtick_labelsize is None:
            xtick_labelsize = "x-large"
        if ytick_labelsize is None:
            ytick_labelsize = "x-large"
    params = {
        "legend.fontsize": "large",
        "axes.labelsize": "x-large",
        "axes.titlesize": "x-large",
        "xtick.labelsize": xtick_labelsize,
        "ytick.labelsize": ytick_labelsize,
    }
    pylab.rcParams.update(params)

    if fig is None and ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    axes = [ax] + [ax.twinx() for i in range(N - 1)]

    for i, ax_y in enumerate(axes):
        ax_y.set_ylim(ymins[i], ymaxs[i])
        ax_y.spines["top"].set_visible(False)
        ax_y.spines["bottom"].set_visible(False)
        if ax_y == ax:
            ax_y.spines["left"].set_position(("data", i))
        if ax_y != ax:
            ax_y.spines["left"].set_visible(False)
            ax_y.yaxis.set_ticks_position("right")
            ax_y.spines["right"].set_position(("data", i))

    # Population distribuion on each vertical axis
    if show_boxplot or show_violin:
        y = [zs[:, i] for i in range(N)]
        y_filtered = [
            y_i[~np.isnan(y_i)] for y_i in y
        ]  # Remove NaN value for box/violin plot

        # Box plot
        if show_boxplot:
            box = ax.boxplot(
                y_filtered, positions=range(N), patch_artist=True, widths=0.15
            )
            for item in ["boxes", "whiskers", "fliers", "medians", "caps"]:
                plt.setp(box[item], color="darkgrey")
            plt.setp(box["boxes"], facecolor="None")
            plt.setp(box["fliers"], markeredgecolor="darkgrey")

        # Violin plot
        if show_violin:
            if model_names2 is None:
                # matplotlib for regular violin plot
                violin = ax.violinplot(
                    y_filtered,
                    positions=range(N),
                    showmeans=False,
                    showmedians=False,
                    showextrema=False,
                )
                for pc in violin["bodies"]:
                    if isinstance(violin_colors, tuple) or isinstance(
                            violin_colors, list
                    ):
                        violin_color = violin_colors[0]
                    else:
                        violin_color = violin_colors
                    pc.set_facecolor(violin_color)
                    pc.set_edgecolor("None")
                    pc.set_alpha(0.8)
            else:
                # seaborn for split violin plot
                violin = sns.violinplot(
                    data=df2_stacked,
                    x="Metric",
                    y="value",
                    ax=ax,
                    hue="group",
                    split=True,
                    linewidth=0.1,
                    scale="count",
                    scale_hue=False,
                    palette={
                        group1_name: violin_colors[0],
                        group2_name: violin_colors[1],
                    },
                )

    # Line or marker

    colors = [plt.get_cmap(colormap)(c) for c in np.linspace(0, 1, len(model_names) + 1)]

    if 'markers' in option:
        marker_types = [option['markers']]
        markers = list(flatten([[marker] * len(colors) for marker in marker_types]))
    else:
        marker_types = ["o", "s", "*", "^", "X", "D", "p"]
        markers = list(flatten([[marker] * len(colors) for marker in marker_types]))

    colors *= len(marker_types)
    mh_index = 0
    for j, model in enumerate(model_names):
        # to just draw straight lines between the axes:
        if model in models_to_highlight:
            if models_to_highlight_colors is not None:
                color = models_to_highlight_colors[mh_index]
            else:
                color = colors[j]

            if models_to_highlight_labels is not None:
                label = models_to_highlight_labels[mh_index]
            else:
                label = model

            if models_to_highlight_by_line:
                ax.plot(range(N), zs[j, :], "-", c=color, label=label, lw=3, markersize=models_to_highlight_markers_size, )
            else:
                ax.plot(
                    range(N),
                    zs[j, :],
                    # models_to_highlight_markers[mh_index],
                    markers[mh_index],
                    c=color,
                    label=label,
                    markersize=models_to_highlight_markers_size,
                    alpha=option['markersalpha'],
                )

            mh_index += 1
        else:
            if identify_all_models:
                ax.plot(
                    range(N),
                    zs[j, :],
                    markers[j],
                    c=colors[j],
                    label=model,
                    clip_on=False,
                    markersize=models_to_highlight_markers_size
                )

    if vertical_center_line:
        if vertical_center_line_label is None:
            vertical_center_line_label = str(vertical_center)
        elif vertical_center_line_label == "off":
            vertical_center_line_label = None
        ax.plot(range(N), zs_middle, "-", c="k", label=vertical_center_line_label, lw=1)

    # Compare two models
    if comparing_models is not None:
        if isinstance(comparing_models, tuple) or (
                isinstance(comparing_models, list) and len(comparing_models) == 2
        ):
            x = range(N)
            m1 = model_names.index(comparing_models[0])
            m2 = model_names.index(comparing_models[1])
            y1 = zs[m1, :]
            y2 = zs[m2, :]

            # Fill between lines
            if fill_between_lines:
                ax.fill_between(
                    x,
                    y1,
                    y2,
                    where=(y2 > y1),
                    facecolor=fill_between_lines_colors[0],
                    interpolate=False,
                    alpha=0.5,
                )
                ax.fill_between(
                    x,
                    y1,
                    y2,
                    where=(y2 < y1),
                    facecolor=fill_between_lines_colors[1],
                    interpolate=False,
                    alpha=0.5,
                )

            # Add vertical arrows
            if arrow_between_lines:
                for xi, yi1, yi2 in zip(x, y1, y2):
                    if yi2 > yi1:
                        arrow_color = arrow_between_lines_colors[0]
                    elif yi2 < yi1:
                        arrow_color = arrow_between_lines_colors[1]
                    else:
                        arrow_color = None
                    arrow_length = yi2 - yi1
                    ax.arrow(
                        xi,
                        yi1,
                        0,
                        arrow_length,
                        color=arrow_color,
                        length_includes_head=True,
                        alpha=arrow_alpha,
                        width=arrow_width,
                        linewidth=arrow_linewidth,
                        head_width=arrow_head_width,
                        head_length=arrow_head_length,
                        zorder=999,
                    )

    if option['situation'] == 2:
        if 'x_rotation' in option:
            x_rotation = option["x_rotation"]
        else:
            x_rotation = 0

        if 'x_ha' in option:
            x_ha = option['x_ha']
        else:
            x_ha = 'center'
    else:
        x_rotation = 0
        x_ha = 'center'

    ax.set_xlim(-0.5, N - 0.5)
    ax.set_xticks(range(N))
    ax.set_xticklabels([name.replace('_', ' ') for name in metric_names], fontsize=xtick_labelsize, rotation=x_rotation, ha=x_ha)
    ax.tick_params(axis="x", which="major", pad=7)
    ax.spines["right"].set_visible(False)

    if not legend_off:
        if violin_label is not None:
            # Get all lines for legend
            lines = [violin["bodies"][0]] + ax.lines
            # Get labels for legend
            labels = [violin_label] + [line.get_label() for line in ax.lines]
            # Remove unnessasary lines that its name starts with '_' to avoid the burden of warning message
            lines = [aa for aa, bb in zip(lines, labels) if not bb.startswith("_")]
            labels = [bb for bb in labels if not bb.startswith("_")]
            # Add legend
            ax.legend(
                lines,
                labels,
                loc=legend_loc,
                ncol=legend_ncol,
                bbox_to_anchor=legend_bbox_to_anchor,
                fontsize=legend_fontsize,
            )
        else:
            # Add legend
            ax.legend(
                loc=legend_loc,
                ncol=legend_ncol,
                bbox_to_anchor=legend_bbox_to_anchor,
                fontsize=legend_fontsize,
            )

    return fig, ax
