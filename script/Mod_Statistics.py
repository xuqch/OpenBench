# -*- coding: utf-8 -*-
import numpy as np
import xarray as xr
from scipy import stats
from joblib import Parallel, delayed
import dask.array as da
import os
import glob
import importlib
import logging
from typing import List, Dict, Any, Tuple

import pandas as pd
import re
import gc
from joblib import Parallel, delayed
import warnings
from dask.diagnostics import ProgressBar
import shutil
from regrid.regrid_wgs84 import convert_to_wgs84_scipy, convert_to_wgs84_xesmf
from figlib import *
from Mod_DatasetProcessing import BaseDatasetProcessing
from Mod_Converttype import Convert_Type

warnings.simplefilter(action='ignore', category=RuntimeWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)


class statistics_calculate:
    """
    A class for performing various statistical analyses on xarray datasets.
    """

    def __init__(self, info):
        """
        Initialize the Statistics class.

        Args:
            info (dict): A dictionary containing additional information to be added as attributes.
        """
        self.name = 'statistics'
        self.version = '0.2'
        self.release = '0.2'
        self.date = 'Mar 2024'
        self.author = "Zhongwang Wei"
        self.__dict__.update(info)

    # Basic statistical methods
    def stat_correlation(self, data1, data2):
        """
        Calculate the correlation coefficient between two datasets.

        Args:
            data1 (xarray.DataArray or xarray.Dataset): First dataset
            data2 (xarray.DataArray or xarray.Dataset): Second dataset

        Returns:
            xarray.DataArray: Correlation coefficient between the two datasets
        """
        if isinstance(data1, xr.Dataset) and isinstance(data2, xr.Dataset):
            # Assume single-variable datasets and extract the variable
            data1 = list(data1.data_vars.values())[0]
            data2 = list(data2.data_vars.values())[0]

        if isinstance(data1, xr.DataArray) and isinstance(data2, xr.DataArray):
            return xr.corr(data1, data2, dim="time").to_dataset(name=f"Correlation")
        else:
            logging.error("Input must be either two xarray Datasets with single variables or two xarray DataArrays")
            raise TypeError("Input must be either two xarray Datasets with single variables or two xarray DataArrays")

    def stat_standard_deviation(self, data):
        """
        Calculate the standard deviation of the input data.

        Args:
            data (xarray.DataArray): Input data

        Returns:
            xarray.DataArray: Standard deviation of the input data
        """
        if isinstance(data, xr.Dataset):
            data = list(data.data_vars.values())[0]
        return data.std(dim="time")

    def stat_z_score(self, data):
        """
        Calculate the Z-score of the input data.

        Args:
            data (xarray.DataArray): Input data

        Returns:
            xarray.DataArray: Z-score of the input data
        """
        if isinstance(data, xr.Dataset):
            data = list(data.data_vars.values())[0]

        # Check if 'time' dimension exists
        if 'time' not in data.dims:
            raise ValueError("Input data must have a 'time' dimension")

        # Calculate mean and std with skipna=True for consistency with other methods
        mean = data.mean(dim="time", skipna=True)
        std = data.std(dim="time", skipna=True)

        # Handle zero or near-zero standard deviation to avoid division by zero
        # Create a mask where std is too small (effectively zero)
        std_mask = std < 1e-10

        # Calculate z-score, safely handling potential division by zero
        # First do the calculation normally
        z_score = (data - mean) / std

        # Then replace values where std is too small with NaN
        if std_mask.any():
            # Where std is effectively zero, set z-score to NaN
            z_score = z_score.where(~std_mask)

        # Add appropriate metadata
        if hasattr(data, 'name') and data.name is not None:
            z_score.name = f"{data.name}_zscore"
        else:
            z_score.name = "zscore"

        # Copy attributes from original data and add z-score specific ones
        z_score.attrs.update(data.attrs)
        z_score.attrs['long_name'] = 'Z-score (standardized anomaly)'
        z_score.attrs['description'] = 'Standardized anomaly: (data - mean) / standard deviation'
        z_score.attrs['units'] = 'unitless'  # Z-scores are dimensionless

        return z_score

    def stat_mean(self, data):
        """
        Calculate the mean of the input data.

        Args:
            data (xarray.DataArray): Input data

        Returns:
            xarray.DataArray: Mean of the input data
        """
        return data.mean(dim="time", skipna=True)

    def stat_median(self, data):
        """
        Calculate the median of the input data.

        Args:
            data (xarray.DataArray): Input data

        Returns:
            xarray.DataArray: Median of the input data
        """
        return data.median(dim="time", skipna=True)

    def stat_max(self, data):
        """
        Calculate the max of the input data.

        Args:
            data (xarray.DataArray): Input data

        Returns:
            xarray.DataArray: Max of the input data
        """
        return data.max(dim="time", skipna=True)

    def stat_min(self, data):
        """
        Calculate the min of the input data.

        Args:
            data (xarray.DataArray): Input data

        Returns:
            xarray.DataArray: Min of the input data
        """
        return data.min(dim="time", skipna=True)

    def stat_sum(self, data):
        """
        Calculate the sum of the input data.

        Args:
            data (xarray.DataArray): Input data

        Returns:
            xarray.DataArray: Sum of the input data
        """
        return data.sum(dim="time", skipna=True)

    def stat_variance(self, data):
        """
        Calculate the variance of the input data.

        Args:
            data (xarray.DataArray): Input data

        Returns:
            xarray.DataArray: Variance of the input data
        """
        return data.var(dim="time")

    def stat_covariance(self, data1, data2):
        """
        Calculate the covariance of the input data.

        Args:
            data1 (xarray.DataArray): First dataset
            data2 (xarray.DataArray): Second dataset

        Returns:
            xarray.DataArray: Covariance of the input data
        """
        return xr.cov(data1, data2, dim="time")

    def stat_autocorrelation(self, data):
        """
        Calculate the autocorrelation of the input data.

        Args:
            data (xarray.DataArray): Input data

        Returns:
            xarray.DataArray: Autocorrelation of the input data
        """
        return data.autocorr(dim="time")

    def stat_diff(self, data):
        """
        Calculate the difference of the input data.

        Args:
            data (xarray.DataArray): Input data

        Returns:
            xarray.DataArray: Difference of the input data
        """
        return data.diff(dim="time")

    def stat_resample(self, data, time):
        """
        Resample the input data.

        Args:
            data (xarray.DataArray): Input data
            time (str): Resampling frequency

        Returns:
            xarray.DataArray: Resampled data
        """
        return data.resample(time)

    def stat_rolling(self, data, window):
        """
        Rolling window of the input data.

        Args:
            data (xarray.DataArray): Input data
            window (int): Window size

        Returns:
            xarray.DataArray: Rolling window of the input data
        """
        return data.rolling(time=window)

    # Advanced statistical methods
    def stat_functional_response(self, v, u):
        """
        Calculate the functional response score for each grid point along the time dimension.

        Args:
            v (xarray.DataArray): Dependent variable
            u (xarray.DataArray): Independent variable
            nbins (int): Number of bins for the histogram
            output_file (str): Name of the output NetCDF file

        Returns:
            xarray.DataArray: Functional response score for each grid point
        """
        import pandas as pd

        if isinstance(v, xr.Dataset):
            v = list(v.data_vars.values())[0]
        if isinstance(u, xr.Dataset):
            u = list(u.data_vars.values())[0]

        try:
            nbins = self.stats_nml['Functional_Response']['nbins']
        except:
            nbins = self.compare_nml['Functional_Response']['nbins']

        def calc_functional_response(v_series, u_series):
            # Remove NaN values
            mask = ~np.isnan(v_series) & ~np.isnan(u_series)
            v_valid = v_series[mask]
            u_valid = u_series[mask]

            if len(v_valid) < 2:  # Not enough data points
                return np.nan

            # Create bins
            if u_valid.min() == u_valid.max():
                return np.nan

            u_bins = np.linspace(u_valid.min(), u_valid.max(), nbins + 1)

            # Calculate mean v for each bin
            df = pd.DataFrame({'u': u_valid, 'v': v_valid})
            binned_means = df.groupby(pd.cut(df['u'], bins=u_bins))['v'].mean()

            df['bin'] = pd.cut(df['u'], bins=u_bins)
            df['v_binned'] = df['bin'].map(binned_means)

            # Calculate RMSE
            rmse = np.sqrt(np.mean((df['v_binned'].astype(float) - df['v'].astype(float)) ** 2))

            # Calculate relative error
            relative_error = rmse / np.mean(v_valid)

            # Calculate score
            score = np.exp(-relative_error)

            return score

        # Apply the function to each grid point
        score = xr.apply_ufunc(
            calc_functional_response,
            v, u,
            input_core_dims=[['time'], ['time']],
            vectorize=True,
            dask='parallelized',
            output_dtypes=[float]
        )

        # Add attributes to the DataArray
        v_name = v.name if v.name is not None else 'unknown'
        u_name = u.name if u.name is not None else 'unknown'
        score.name = 'functional_response_score'
        score.attrs['long_name'] = 'Functional Response Score'
        score.attrs['units'] = '1'
        score.attrs['description'] = 'Functional response score calculated between variables ' + u_name + ' and ' + v_name
        # Create a dataset with the score
        ds = xr.Dataset({'functional_response_score': score})
        del score

        # Add global attributes
        ds.attrs['title'] = 'Functional Response Score'
        ds.attrs['description'] = 'Functional response score calculated between variables ' + u_name + ' and ' + v_name
        ds.attrs['created_by'] = 'ILAMB var_functional_response function'

        return ds

    def stat_hellinger_distance(self, v, u):
        """
        Calculate the Hellinger Distance score for each grid point along the time dimension.

        Args:
            v (xarray.DataArray): First variable
            u (xarray.DataArray): Second variable
            nbins (int): Number of bins for the 2D histogram
            output_file (str): Name of the output NetCDF file

        Returns:
            xarray.DataArray: Hellinger Distance score for each grid point
        """
        nbins = self.stats_nml['Hellinger_Distance']['nbins']

        if isinstance(v, xr.Dataset):
            v = list(v.data_vars.values())[0]
        if isinstance(u, xr.Dataset):
            u = list(u.data_vars.values())[0]

        def calc_hellinger_distance(v_series, u_series):
            # Remove NaN values
            mask = ~np.isnan(v_series) & ~np.isnan(u_series)
            v_valid = v_series[mask]
            u_valid = u_series[mask]

            if len(v_valid) < 2:  # Not enough data points
                return np.nan

            # Calculate 2D histogram
            hist, _, _ = np.histogram2d(v_valid, u_valid, bins=nbins)

            # Normalize the histogram
            hist = hist / hist.sum()

            # Calculate Hellinger distance

            # 公式计算问题
            # hellinger_dist = np.sqrt(1 - np.sum(np.sqrt(hist)))
            hellinger_dist = np.sqrt(np.sum(np.sqrt(hist)))

            # print(hist)
            # print(type(hist))
            # print(hellinger_dist)
            # print(type(hellinger_dist))

            return hellinger_dist

        # Apply the function to each grid point
        score = xr.apply_ufunc(
            calc_hellinger_distance,
            v, u,
            input_core_dims=[['time'], ['time']],
            vectorize=True,
            dask='parallelized',
            output_dtypes=[float]
        )

        # Add attributes to the DataArray
        v_name = v.name if v.name is not None else 'unknown'
        u_name = u.name if u.name is not None else 'unknown'
        score.name = 'hellinger_distance_score'
        score.attrs['long_name'] = 'Hellinger Distance Score'
        score.attrs['units'] = '-'
        score.attrs['description'] = 'Hellinger Distance score calculated between variables ' + u_name + ' and ' + v_name

        # Create a dataset with the score
        ds = xr.Dataset({'hellinger_distance_score': score})
        del score
        # Add global attributes
        ds.attrs['title'] = 'Hellinger Distance Score'
        ds.attrs['description'] = 'Hellinger Distance score calculated between variables ' + u_name + ' and ' + v_name
        ds.attrs['created_by'] = 'ILAMB var_hellinger_distance function'

        return ds

    def stat_three_cornered_hat(self, *variables):
        """
        Calculate uncertainty using the Three-Cornered Hat method.

        Args:
            *variables: Variable number of xarray DataArrays to compare.
                       Requires at least 3 variables for the method to work.

        Returns:
            xarray.Dataset: Dataset containing uncertainty and relative uncertainty
        """
        try:
            from scipy import optimize
            import gc
        except ImportError as e:
            logging.error(f"Required package not found: {e}")
            raise ImportError(f"Required package not found: {e}")

        # Check if we have enough variables
        if len(variables) < 3:
            raise ValueError("Three-Cornered Hat method requires at least 3 variables")

        def cal_uct(arr):
            """Calculate uncertainty using Three-Cornered Hat method for one grid point."""
            try:
                # Check if we have enough valid data
                if np.isnan(arr).any() or arr.shape[0] < 3 or arr.shape[1] < 3:
                    return np.full(arr.shape[1], np.nan), np.full(arr.shape[1], np.nan)

                def my_fun(r):
                    """Objective function for optimization."""
                    try:
                        S = np.cov(arr.T)
                        f = np.sum(r[:-1] ** 2)
                        for j in range(len(S)):
                            for k in range(j + 1, len(S)):
                                f += (S[j, k] - r[-1] + r[j] + r[k]) ** 2
                        K = np.linalg.det(S)
                        # Avoid division by zero or very small determinants
                        if abs(K) < 1e-10:
                            return np.inf
                        F = f / (K ** (2 * len(S)))
                        return F
                    except Exception as e:
                        logging.debug(f"Error in objective function: {e}")
                        return np.inf

                S = np.cov(arr.T)
                # Check if covariance matrix is valid
                if np.isnan(S).any() or np.isinf(S).any():
                    return np.full(arr.shape[1], np.nan), np.full(arr.shape[1], np.nan)

                det_S = np.linalg.det(S)
                # Check if matrix is singular or nearly singular
                if abs(det_S) < 1e-10:
                    return np.full(arr.shape[1], np.nan), np.full(arr.shape[1], np.nan)

                N = arr.shape[1]
                u = np.ones((1, N - 1))
                R = np.zeros((N, N))

                try:
                    inv_S = np.linalg.inv(S)
                    inv_S_sub = inv_S[:N-1, :N-1] # Submatrix for calculations involving u
                    # Use inv_S_sub for dot product with u
                    R[N - 1, N - 1] = 1 / (2 * np.dot(np.dot(u, inv_S_sub), u.T))
                except np.linalg.LinAlgError:
                    print(f"DEBUG: cal_uct returning NaN - LinAlgError during initial R calculation")
                    return np.full(arr.shape[1], np.nan), np.full(arr.shape[1], np.nan)

                x0 = R[:, N - 1]
                Denominator = det_S ** (2 / len(S))

                # Set up constraint
                # Use inv_S_sub in the constraint lambda function as well
                cons = {'type': 'ineq', 'fun': lambda r: (r[-1] - np.dot(
                    np.dot(r[:-1] - r[-1] * u, inv_S_sub),
                    (r[:-1] - r[-1] * u).T)) / Denominator}

                # Perform optimization with error handling
                try:
                    x = optimize.minimize(my_fun, x0, method='COBYLA', tol=2e-10, constraints=cons)
                    if not x.success:
                        return np.full(arr.shape[1], np.nan), np.full(arr.shape[1], np.nan)

                    R[:, N - 1] = x.x
                    for i in range(N - 1):
                        for j in range(i, N - 1):
                            R[i, j] = S[i, j] - R[N - 1, N - 1] + R[i, N - 1] + R[j, N - 1]
                    R += R.T - np.diag(R.diagonal())

                    diag_R = np.diag(R)
                    # Check if R has negative values on diagonal (invalid results)
                    if np.any(diag_R < 0):
                        return np.full(arr.shape[1], np.nan), np.full(arr.shape[1], np.nan)

                    uct = np.sqrt(diag_R) # Use pre-calculated diagonal

                    # Safely calculate relative uncertainty
                    mean_abs = np.mean(np.abs(arr), axis=0)
                    # Avoid division by zero
                    mean_abs_safe = np.where(mean_abs < 1e-10, np.nan, mean_abs)
                    
                    if np.isnan(mean_abs_safe).any():
                        print(f"DEBUG: cal_uct returning NaN - mean_abs is NaN (near zero: {mean_abs})")
                        return np.full(arr.shape[1], np.nan), np.full(arr.shape[1], np.nan)
                        
                    r_uct = uct / mean_abs_safe * 100

                    return uct, r_uct
                except Exception as e:
                    # Optionally re-raise or log traceback here for more detail
                    import traceback
                    traceback.print_exc()
                    return np.full(arr.shape[1], np.nan), np.full(arr.shape[1], np.nan)
            except Exception as e:
                print(f"DEBUG: cal_uct returning NaN due to outer exception: {e}")
                return np.full(arr.shape[1], np.nan), np.full(arr.shape[1], np.nan)

        try:
            # Extract data from each dataset if it's a Dataset
            data_arrays = []
            for var in variables:
                if isinstance(var, xr.Dataset):
                    # Get the first data variable from the dataset
                    var_name = list(var.data_vars)[0]
                    data_arrays.append(var[var_name])
                else:
                    # Already a DataArray
                    data_arrays.append(var)
            
            # Combine all variables into a single array
            combined_data = xr.concat(data_arrays, dim='variable')
            #save the combined_data
            combined_data.to_netcdf('combined_data.nc')
            # Get dimensions for processing
            lats = combined_data.lat.values
            lons = combined_data.lon.values
            num_variables = len(data_arrays)

            # Initialize output arrays with NaN values - WITHOUT time dimension
            empty_template = xr.DataArray(
                np.full((num_variables, len(lats), len(lons)), np.nan),
                dims=('variable', 'lat', 'lon'),
                coords={'variable': range(num_variables), 'lat': lats, 'lon': lons}
            )
            uct = empty_template.copy()
            r_uct = empty_template.copy()

            # Process in chunks to manage memory better
            # Use joblib to parallelize if data is large enough
            if len(lats) * len(lons) > 100:  # Arbitrary threshold for parallelization
                from joblib import Parallel, delayed

                def process_chunk(lat_chunk):
                    """Process a chunk of latitudes in parallel."""
                    chunk_results = []
                    for lat in lat_chunk:
                        for lon in lons:
                            # Extract numerical values only, ensure it's a proper numpy array
                            arr = combined_data.sel(lat=lat, lon=lon).values
                            if not isinstance(arr, np.ndarray) or arr.size == 0 or np.isnan(arr).all():
                                continue
                            
                            # For Three-Cornered Hat method, we need to transpose the data
                            # so that time is the first dimension and variables are the second
                            arr = arr.T  # shape: (time, variables)
                            uct_values, r_uct_values = cal_uct(arr)
                            chunk_results.append((lat, lon, uct_values, r_uct_values))
                    return chunk_results

                # Split lats into chunks for parallel processing
                n_jobs = min(os.cpu_count(), 8)  # Limit to avoid excessive memory use
                chunk_size = max(1, len(lats) // (n_jobs * 2))
                lat_chunks = [lats[i:i + chunk_size] for i in range(0, len(lats), chunk_size)]

                # Process chunks in parallel
                all_results = Parallel(n_jobs=n_jobs)(
                    delayed(process_chunk)(chunk) for chunk in lat_chunks
                )

                # Combine results
                for chunk_results in all_results:
                    for lat, lon, uct_values, r_uct_values in chunk_results:
                        # Use .loc indexing to set values
                        lat_idx = np.where(lats == lat)[0][0]
                        lon_idx = np.where(lons == lon)[0][0]
                        uct.values[:, lat_idx, lon_idx] = uct_values
                        r_uct.values[:, lat_idx, lon_idx] = r_uct_values

                # Clean up
                del all_results
                gc.collect()
            else:
                # For smaller datasets, use simple loop
                for lat in lats:
                    for lon in lons:
                        arr = combined_data.sel(lat=lat, lon=lon).values
                        if isinstance(arr, np.ndarray) and arr.size > 0 and not np.isnan(arr).all():
                            # For Three-Cornered Hat method, transpose the data
                            arr = arr.T  # shape: (time, variables)
                            
                            uct_values, r_uct_values = cal_uct(arr)
                            
                            # Use direct indexing
                            lat_idx = np.where(lats == lat)[0][0]
                            lon_idx = np.where(lons == lon)[0][0]
                            uct.values[:, lat_idx, lon_idx] = uct_values
                            r_uct.values[:, lat_idx, lon_idx] = r_uct_values
                    
                    # Periodically collect garbage to manage memory
                    if lat % 10 == 0:
                        gc.collect()

            # Create output dataset
            ds = xr.Dataset({
                'uncertainty': uct,
                'relative_uncertainty': r_uct
            })

            # Add metadata
            ds['uncertainty'].attrs['long_name'] = 'Uncertainty from Three-Cornered Hat method'
            ds['uncertainty'].attrs['units'] = 'Same as input variables'
            ds['uncertainty'].attrs['description'] = 'Absolute uncertainty estimated using the Three-Cornered Hat method'
            ds['relative_uncertainty'].attrs['long_name'] = 'Relative uncertainty from Three-Cornered Hat method'
            ds['relative_uncertainty'].attrs['units'] = '%'
            ds['relative_uncertainty'].attrs['description'] = 'Relative uncertainty (%) estimated using the Three-Cornered Hat method'
            ds.attrs['method'] = 'Three-Cornered Hat'
            ds.attrs['n_datasets'] = len(variables)

            return ds

        finally:
            # Clean up memory
            gc.collect()


    def stat_partial_least_squares_regression(self, *variables):
        """
        Calculate the Partial Least Squares Regression (PLSR) analysis with cross-validation and parallel processing.

        Args:
            *variables: Variable number of xarray DataArrays. One should have '_Y' in its name as the dependent variable.
            max_components (int): Maximum number of components to consider
            n_splits (int): Number of splits for time series cross-validation
            n_jobs (int): Number of jobs for parallel processing

        Returns:
            xarray.Dataset: Dataset containing PLSR results
        """
        try:
            from sklearn.cross_decomposition import PLSRegression
            from sklearn.model_selection import cross_val_score, TimeSeriesSplit
        except ImportError:
            logging.error("scikit-learn is required for this function")
            raise ImportError("scikit-learn is required for this function")
        from scipy.stats import t

        # Prepare Dependent and Independent data
        max_components = self.stats_nml['Partial_Least_Squares_Regression']['max_components']
        n_splits = self.stats_nml['Partial_Least_Squares_Regression']['n_splits']
        n_jobs = self.stats_nml['Partial_Least_Squares_Regression']['n_jobs']

        Y_vars = variables[0]  # [var for var in variables if '_Y' in var.name]
        X_vars = list(variables[1:])  # [var for var in variables if '_Y' not in var.name]

        def extract_xarray_data(data):
            """统一提取 xarray.Dataset 或 xarray.DataArray 的数据"""
            if isinstance(data, xr.Dataset):
                return data.to_array().squeeze("variable").values  # Dataset → 转多变量DataArray再取值
            elif isinstance(data, xr.DataArray):
                return data.values  # DataArray → 直接取值
            else:
                raise TypeError(f"Unsupported type: {type(data)}. Expected xarray.Dataset or xarray.DataArray")

        # Prepare data
        Y_data = extract_xarray_data(Y_vars)
        X_data = np.concatenate([extract_xarray_data(x)[np.newaxis, ...] for x in X_vars], axis=0)
        X_data = np.moveaxis(X_data, 0, 1)  # Reshape to (time, n_variables, lat, lon)
        # Standardize data
        X_mean = np.mean(X_data, axis=0)
        X_std = np.std(X_data, axis=0)
        X_stand = (X_data - X_mean) / X_std

        Y_mean = np.mean(Y_data, axis=0)
        Y_std = np.std(Y_data, axis=0)
        Y_stand = (Y_data - Y_mean) / Y_std

        # Define helper functions for parallel processing
        def compute_best_components(lat, lon):
            x = X_stand[:, :, lat, lon]
            y = Y_stand[:, lat, lon]
            if np.isnan(x).any() or np.isnan(y).any():
                return lat, lon, np.nan

            tscv = TimeSeriesSplit(n_splits=n_splits)
            scores = []
            for n in range(1, max_components + 1):
                pls = PLSRegression(n_components=n, scale=False, max_iter=500)
                score = cross_val_score(pls, x, y, cv=tscv)
                scores.append(score.mean())

            best_n_components = np.argmax(scores) + 1
            return lat, lon, best_n_components

        def compute_plsr(lat, lon, n_components):
            x = X_stand[:, :, lat, lon]
            y = Y_stand[:, lat, lon]
            if np.isnan(x).any() or np.isnan(y).any():
                return lat, lon, np.full(X_data.shape[1], np.nan), np.nan, np.full(X_data.shape[1], np.nan), np.nan

            pls = PLSRegression(n_components=n_components, scale=False)
            pls.fit(x, y)
            coef = pls.coef_.T
            intercept = pls.intercept_.T
            residuals = y - pls.predict(x).ravel()
            mse = np.mean(residuals ** 2)
            coef_std_err = np.sqrt(mse / len(y))
            df = len(y) - 1
            t_vals = coef.ravel() / coef_std_err
            p_vals = 2 * (1 - t.cdf(np.abs(t_vals), df))
            r_squared = pls.score(x, y)

            return lat, lon, coef.ravel(), intercept.ravel(), p_vals, r_squared
            # Compute best number of components

        results = Parallel(n_jobs=n_jobs)(
            delayed(compute_best_components)(lat, lon)
            for lat in range(Y_data.shape[1]) for lon in range(Y_data.shape[2])
        )

        best_n_components = np.zeros((Y_data.shape[1], Y_data.shape[2]), dtype=int)
        for lat, lon, n_components in results:
            if not np.isnan(n_components):
                best_n_components[lat, lon] = n_components

        # Compute PLSR results
        results = Parallel(n_jobs=n_jobs)(
            delayed(compute_plsr)(lat, lon, best_n_components[lat, lon])
            for lat in range(Y_data.shape[1]) for lon in range(Y_data.shape[2])
        )

        coef_values = np.zeros((X_data.shape[1], Y_data.shape[1], Y_data.shape[2]))
        intercept_values = np.zeros((X_data.shape[1], Y_data.shape[1], Y_data.shape[2]))
        p_values = np.zeros((X_data.shape[1], Y_data.shape[1], Y_data.shape[2]))
        r_squared_values = np.zeros((Y_data.shape[1], Y_data.shape[2]))

        for lat, lon, coef, intercept, p_vals, r_squared in results:
            coef_values[:, lat, lon] = coef
            intercept_values[:, lat, lon] = intercept
            p_values[:, lat, lon] = p_vals
            r_squared_values[lat, lon] = r_squared

        # Calculate anomaly
        anomaly = coef_values * Y_std[np.newaxis, :, :]
        # Create output dataset
        ds = xr.Dataset(
            data_vars={
                'best_n_components': (['lat', 'lon'], best_n_components),
                'coefficients': (['variable', 'lat', 'lon'], coef_values),
                'intercepts': (['variable', 'lat', 'lon'], intercept_values),
                'p_values': (['variable', 'lat', 'lon'], p_values),
                'r_squared': (['lat', 'lon'], r_squared_values),
                'anomaly': (['variable', 'lat', 'lon'], anomaly)
            },
            coords={
                'lat': Y_vars.lat,
                'lon': Y_vars.lon,
                'variable': [f'x{i + 1}' for i in range(len(X_vars))]
            }
        )

        # Add metadata
        ds['best_n_components'].attrs['long_name'] = 'Best number of components'
        ds['coefficients'].attrs['long_name'] = 'PLSR coefficients'
        ds['intercepts'].attrs['long_name'] = 'PLSR intercepts'
        ds['p_values'].attrs['long_name'] = 'P-values'
        ds['r_squared'].attrs['long_name'] = 'R-squared'
        ds['anomaly'].attrs['long_name'] = 'Anomaly (coefficients * Y standard deviation)'

        return ds

    def stat_mann_kendall_trend_test(self, data):
        """
        Calculates the Mann-Kendall trend test for a time series using scipy's kendalltau.

        Args:
            data (xarray.Dataset or xarray.DataArray): Time series data.

        Returns:
            xarray.Dataset: Dataset containing trend test results for each variable and grid point.
        """
        try:
            significance_level = self.stats_nml['Mann_Kendall_Trend_Test']['significance_level']
        except:
            significance_level = self.compare_nml['Mann_Kendall_Trend_Test']['significance_level']

        def _apply_mann_kendall(da, significance_level):
            """
            Applies Mann-Kendall test to a single DataArray using kendalltau.
            """

            def mk_test(x):
                if len(x) < 4 or np.all(np.isnan(x)):
                    return np.array([np.nan, np.nan, np.nan, np.nan])

                # Remove NaN values
                x = x[~np.isnan(x)]

                if len(x) < 4:
                    return np.array([np.nan, np.nan, np.nan, np.nan])

                # Calculate Kendall's tau and p-value
                tau, p_value = stats.kendalltau(np.arange(len(x)), x)

                # Determine trend
                trend = np.sign(tau)
                significance = p_value < significance_level

                return np.array([trend, significance, p_value, tau])

            try:
                # Apply the test to each grid point with chunking
                result = xr.apply_ufunc(
                    mk_test,
                    da,
                    input_core_dims=[['time']],
                    output_core_dims=[['mk_params']],
                    vectorize=True,
                    dask='parallelized',
                    output_dtypes=[float],
                    output_sizes={'mk_params': 4}
                )

                # Create separate variables for each component
                trend = result.isel(mk_params=0)
                significance = result.isel(mk_params=1)
                p_value = result.isel(mk_params=2)
                tau = result.isel(mk_params=3)

                # Create a new Dataset with separate variables
                ds = xr.Dataset({
                    'trend': trend,
                    'significance': significance,
                    'p_value': p_value,
                    'tau': tau
                })

                # Add attributes
                ds.trend.attrs['long_name'] = 'Mann-Kendall trend'
                ds.trend.attrs['description'] = 'Trend direction: 1 (increasing), -1 (decreasing), 0 (no trend)'
                ds.significance.attrs['long_name'] = 'Trend significance'
                ds.significance.attrs['description'] = f'True if trend is significant at {significance_level} level, False otherwise'
                ds.p_value.attrs['long_name'] = 'p-value'
                ds.p_value.attrs['description'] = 'p-value of the Mann-Kendall trend test'
                ds.tau.attrs['long_name'] = "Kendall's tau statistic"
                ds.tau.attrs['description'] = "Kendall's tau correlation coefficient"

                ds.attrs['statistical_test'] = 'Mann-Kendall trend test (using Kendall\'s tau)'
                ds.attrs['significance_level'] = significance_level

                # Clean up intermediate result
                del result
                gc.collect()

                return ds
            finally:
                # Ensure cleanup of any remaining objects
                gc.collect()

        try:
            # Process the data with proper memory management
            if isinstance(data, xr.Dataset):
                # If it's a dataset, apply the test to each data variable
                results = []
                for var in data.data_vars:
                    result = _apply_mann_kendall(data[var], significance_level)
                    result = result.assign_coords(variable=var)
                    results.append(result)
                # Save the result
                return xr.concat(results, dim='variable')
            elif isinstance(data, xr.DataArray):
                # If it's a DataArray, apply the test directly
                return _apply_mann_kendall(data, significance_level)
            else:
                logging.error("Input must be an xarray Dataset or DataArray")
                raise TypeError("Input must be an xarray Dataset or DataArray")

        finally:
            # Clean up any remaining objects
            gc.collect()

    def stat_False_Discovery_Rate(self, *variables, alpha=0.05):
        """
        Perform optimized False Discovery Rate (FDR) analysis on multiple xarray datasets.

        Args:
            *variables: Variable number of xarray DataArrays to compare
            alpha (float): FDR control level, default is 0.05

        Returns:
            xarray.Dataset: Dataset containing p-values, FDR results, and metadata
        """

        def vectorized_ttest(a, b):
            a_mean = a.mean(dim='time')
            b_mean = b.mean(dim='time')
            a_var = a.var(dim='time')
            b_var = b.var(dim='time')
            a_count = a.count(dim='time')
            b_count = b.count(dim='time')

            t = (a_mean - b_mean) / da.sqrt(a_var / a_count + b_var / b_count)
            df = (a_var / a_count + b_var / b_count) ** 2 / (
                    (a_var / a_count) ** 2 / (a_count - 1) + (b_var / b_count) ** 2 / (b_count - 1)
            )

            # Use dask's map_overlap for efficient computation
            prob = da.map_overlap(
                lambda x, y: stats.t.sf(np.abs(x), y) * 2,
                t.data, df.data,
                depth=(0,) * t.ndim,
                boundary='none'
            )
            return xr.DataArray(prob, coords=t.coords, dims=t.dims)

        def apply_fdr(p_values, alpha):
            p_sorted = da.sort(p_values.data.ravel())
            m = p_sorted.size
            thresholds = da.arange(1, m + 1) / m * alpha
            significant = p_sorted <= thresholds
            if da.any(significant):
                p_threshold = p_sorted[da.argmax(significant[::-1])]
            else:
                p_threshold = 0
            return p_threshold.compute()

        # Compute p-values for all pairs of datasets
        n_datasets = len(variables)
        combinations = [(i, j) for i in range(n_datasets) for j in range(i + 1, n_datasets)]

        # Precompute means and variances
        means = [var.mean(dim='time') for var in variables]
        variances = [var.var(dim='time') for var in variables]
        counts = [var.count(dim='time') for var in variables]

        p_values = []
        for i, j in combinations:
            p_value = vectorized_ttest(variables[i], variables[j])
            p_values.append(p_value)

        p_values = xr.concat(p_values, dim='combination')

        # Apply FDR
        p_threshold = apply_fdr(p_values, alpha)
        significant_mask = p_values <= p_threshold
        proportion_passed = significant_mask.sum('combination') / len(combinations)

        # Create output dataset
        ds = xr.Dataset({
            'p_values': p_values,
            'significant': significant_mask,
            'proportion_passed': proportion_passed
        })

        # Add metadata
        ds['p_values'].attrs['long_name'] = 'P-values from t-test'
        ds['p_values'].attrs['description'] = 'P-values for each combination of datasets'
        ds['significant'].attrs['long_name'] = 'Significant grid points'
        ds['significant'].attrs['description'] = 'Boolean mask of significant grid points'
        ds['proportion_passed'].attrs['long_name'] = 'Proportion of tests passed FDR'
        ds['proportion_passed'].attrs['description'] = 'Proportion of tests that passed the FDR threshold'
        ds.attrs['FDR_threshold'] = p_threshold
        ds.attrs['alpha_FDR'] = alpha

        return ds

    def stat_anova(self, *variables):
        """
        Perform statistical analysis (one-way ANOVA or two-way ANOVA) on multiple variables,
        automatically identifying the dependent variable.

        Args:
           *variables: Variable number of xarray DataArrays. The one with '_Y' in its name is treated as the dependent variable.
           n_jobs (int): Number of jobs for parallel processing. Default is -1 (use all cores)
           analysis_type (str): Type of analysis to perform. 'oneway' for one-way ANOVA, 'twoway' for two-way ANOVA

        Returns:
           xarray.Dataset: Dataset containing results of the analysis (F-statistic and p-values for one-way ANOVA,
                          sum of squares and p-values for two-way ANOVA)
        """
        # , n_jobs = -1, analysis_type = 'twoway'
        n_jobs = self.stats_nml['ANOVA']['n_jobs']
        analysis_type = self.stats_nml['ANOVA']['analysis_type']

        try:
            if analysis_type == 'twoway':
                import statsmodels.formula.api as smf
                import statsmodels.api as sm
                from scipy.stats import t

            elif analysis_type == 'oneway':
                from scipy.stats import f_oneway
            else:
                logging.error("Invalid analysis_type. Choose 'oneway' or 'twoway'")
                raise ValueError("Invalid analysis_type. Choose 'oneway' or 'twoway'")
        except ImportError as e:
            logging.error(f"{e.name} is required for this function")
            raise ImportError(f"{e.name} is required for this function")
        from joblib import Parallel, delayed
        import gc

        # Separate dependent and independent variables
        Y_vars = variables[0]  # [var for var in variables if '_Y' in var.name]
        X_vars = variables[1:]  # [var for var in variables if '_Y' not in var.name]

        if len(Y_vars) != 1:
            logging.error("Exactly one variable with '_Y' in its name should be provided as the dependent variable.")
            raise ValueError("Exactly one variable with '_Y' in its name should be provided as the dependent variable.")

        def extract_xarray_data(data):
            """统一提取 xarray.Dataset 或 xarray.DataArray 的数据"""
            if isinstance(data, xr.Dataset):
                varname = next(iter(data.data_vars))
                return data[varname]  # Dataset → 转多变量DataArray再取值
            elif isinstance(data, xr.DataArray):
                return data  # DataArray → 直接取值
            else:
                raise TypeError(f"Unsupported type: {type(data)}. Expected xarray.Dataset or xarray.DataArray")
                # If it's a dataset, apply the test to each data variable

        Y_data = extract_xarray_data(Y_vars)
        # Align and combine datasets
        combined_data = xr.merge([Y_data.rename('Y_data')] + [extract_xarray_data(var).rename(f'var_{i}') for i, var in enumerate(X_vars)])

        # Prepare data for analysis
        data_array = np.stack([combined_data[var].values for var in combined_data.data_vars if var != 'Y_data'], axis=-1)
        Y_data_array = combined_data['Y_data'].values

        # Determine number of cores to use
        num_cores = n_jobs if n_jobs > 0 else os.cpu_count()
        # Limit cores to a reasonable number to avoid memory issues
        num_cores = min(num_cores, os.cpu_count(), 8)

        try:
            if analysis_type == 'twoway':
                def normalize_data(data):
                    """Normalize data to [0, 1] range."""
                    min_val = np.nanmin(data)
                    max_val = np.nanmax(data)
                    if max_val == min_val:
                        return np.zeros_like(data)
                    return (data - min_val) / (max_val - min_val)

                def OLS(data_slice, Y_data_slice):
                    """Perform OLS analysis on a single lat-lon point."""
                    # Check for invalid data
                    if np.any(np.isnan(data_slice)) or np.any(np.isnan(Y_data_slice)) or \
                            np.any(np.isinf(data_slice)) or np.any(np.isinf(Y_data_slice)) or \
                            np.any(np.all(data_slice < 1e-10, axis=0)) or np.all(Y_data_slice < 1e-10) or \
                            len(Y_data_slice) < data_slice.shape[1] + 2:  # Ensure enough samples for model
                        return np.full(data_slice.shape[1] * 2, np.nan), np.full(data_slice.shape[1] * 2, np.nan)

                    try:
                        # Normalize data
                        norm_data = np.apply_along_axis(normalize_data, 0, data_slice)
                        norm_Y_data = normalize_data(Y_data_slice)

                        # Create DataFrame
                        df = pd.DataFrame(norm_data, columns=[f'var_{i}' for i in range(norm_data.shape[1])])
                        df['Y_data'] = norm_Y_data

                        # Construct formula with main effects only
                        var_names = df.columns[:-1]
                        main_effects = '+'.join(var_names)

                        # Add limited interactions - only include first-order interactions
                        # to avoid over-parameterization
                        interactions = ""
                        if len(var_names) > 1:
                            interactions = "+" + '+'.join(f'({a}:{b})'
                                                          for i, a in enumerate(var_names)
                                                          for b in var_names[i + 1:])

                        formula = f'Y_data ~ {main_effects}{interactions}'

                        # Perform OLS
                        model = smf.ols(formula, data=df).fit()
                        anova_results = sm.stats.anova_lm(model, typ=2)

                        return anova_results['sum_sq'].values, anova_results['PR(>F)'].values
                    except Exception as e:
                        logging.debug(f"Error in OLS analysis: {e}")
                        n_factors = data_slice.shape[1] * 2
                        return np.full(n_factors, np.nan), np.full(n_factors, np.nan)

                # Parallel processing with chunking to conserve memory
                chunk_size = max(1, data_array.shape[-3] // (num_cores * 2))
                results = []

                for chunk_i in range(0, data_array.shape[-3], chunk_size):
                    end_i = min(chunk_i + chunk_size, data_array.shape[-3])
                    chunk_results = Parallel(n_jobs=num_cores)(
                        delayed(OLS)(data_array[..., i, j, :], Y_data_array[..., i, j])
                        for i in range(chunk_i, end_i)
                        for j in range(data_array.shape[-2])
                    )
                    results.extend(chunk_results)
                    # Force garbage collection
                    gc.collect()

                # Process results
                if not results:
                    logging.error("No valid results from ANOVA analysis")
                    raise ValueError("No valid results from ANOVA analysis")

                # Determine number of factors from first non-NaN result
                valid_result = next((r for r in results if not np.all(np.isnan(r[0]))), None)
                if valid_result is None:
                    logging.error("All ANOVA results are NaN")
                    raise ValueError("All ANOVA results are NaN")

                n_factors = len(valid_result[0])

                # Reshape results
                sum_sq = np.array([r[0] if len(r[0]) == n_factors else np.full(n_factors, np.nan)
                                   for r in results]).reshape(data_array.shape[-3], data_array.shape[-2], -1)
                p_values = np.array([r[1] if len(r[1]) == n_factors else np.full(n_factors, np.nan)
                                     for r in results]).reshape(data_array.shape[-3], data_array.shape[-2], -1)

                # Create output dataset
                output_ds = xr.Dataset(
                    {
                        'sum_sq': (['lat', 'lon', 'factors'], sum_sq),
                        'p_value': (['lat', 'lon', 'factors'], p_values)
                    },
                    coords={
                        'lat': combined_data.lat,
                        'lon': combined_data.lon,
                        'factors': np.arange(n_factors)
                    }
                )

                # Add metadata
                output_ds['sum_sq'].attrs['long_name'] = 'Sum of Squares from ANOVA'
                output_ds['sum_sq'].attrs['description'] = 'Sum of squares for each factor in the ANOVA'
                output_ds['p_value'].attrs['long_name'] = 'P-values from ANOVA'
                output_ds['p_value'].attrs['description'] = 'P-values for each factor in the ANOVA'
                output_ds.attrs['analysis_type'] = 'two-way ANOVA'
                output_ds.attrs['n_factors'] = n_factors

            elif analysis_type == 'oneway':
                def oneway_anova(data_slice, Y_data_slice):
                    """Perform one-way ANOVA on a single lat-lon point."""
                    if np.any(np.isnan(data_slice)) or np.any(np.isnan(Y_data_slice)) or \
                            np.any(np.isinf(data_slice)) or np.any(np.isinf(Y_data_slice)) or \
                            np.any(np.all(data_slice < 1e-10, axis=0)) or np.all(Y_data_slice < 1e-10):
                        return np.nan, np.nan

                    try:
                        # More robust grouping approach - discretize continuous variables
                        groups = []
                        for i in range(data_slice.shape[1]):
                            # Use quartiles to discretize the data
                            x = data_slice[:, i]
                            x_valid = x[~np.isnan(x)]
                            if len(x_valid) < 4:  # Not enough data for quartiles
                                continue

                            # Calculate quartiles
                            q1, q2, q3 = np.percentile(x_valid, [25, 50, 75])

                            # Group by quartiles
                            g1 = Y_data_slice[(x <= q1) & ~np.isnan(Y_data_slice)]
                            g2 = Y_data_slice[(x > q1) & (x <= q2) & ~np.isnan(Y_data_slice)]
                            g3 = Y_data_slice[(x > q2) & (x <= q3) & ~np.isnan(Y_data_slice)]
                            g4 = Y_data_slice[(x > q3) & ~np.isnan(Y_data_slice)]

                            # Add non-empty groups
                            for g in [g1, g2, g3, g4]:
                                if len(g) >= 2:  # Need at least 2 samples
                                    groups.append(g)

                        if len(groups) < 2:  # Need at least 2 groups for ANOVA
                            return np.nan, np.nan

                        # Perform one-way ANOVA
                        f_statistic, p_value = f_oneway(*groups)
                        return f_statistic, p_value
                    except Exception as e:
                        logging.debug(f"Error in one-way ANOVA: {e}")
                        return np.nan, np.nan

                # Parallel processing with chunking to conserve memory
                chunk_size = max(1, data_array.shape[-3] // (num_cores * 2))
                results = []

                for chunk_i in range(0, data_array.shape[-3], chunk_size):
                    end_i = min(chunk_i + chunk_size, data_array.shape[-3])
                    chunk_results = Parallel(n_jobs=num_cores)(
                        delayed(oneway_anova)(data_array[..., i, j, :], Y_data_array[..., i, j])
                        for i in range(chunk_i, end_i)
                        for j in range(data_array.shape[-2])
                    )
                    results.extend(chunk_results)
                    # Force garbage collection
                    gc.collect()

                # Reshape results
                f_statistics = np.array([r[0] for r in results]).reshape(data_array.shape[-3], data_array.shape[-2])
                p_values = np.array([r[1] for r in results]).reshape(data_array.shape[-3], data_array.shape[-2])

                # Create output dataset
                output_ds = xr.Dataset(
                    {
                        'F_statistic': (['lat', 'lon'], f_statistics),
                        'p_value': (['lat', 'lon'], p_values)
                    },
                    coords={
                        'lat': combined_data.lat,
                        'lon': combined_data.lon,
                    }
                )

                # Add metadata
                output_ds['F_statistic'].attrs['long_name'] = 'F-statistic from one-way ANOVA'
                output_ds['F_statistic'].attrs['description'] = 'F-statistic for the one-way ANOVA'
                output_ds['p_value'].attrs['long_name'] = 'P-values from one-way ANOVA'
                output_ds['p_value'].attrs['description'] = 'P-values for the one-way ANOVA'
                output_ds.attrs['analysis_type'] = 'one-way ANOVA'

            return output_ds

        finally:
            # Clean up memory
            del data_array
            del Y_data_array
            del results
            gc.collect()

    def save_result(self, method_name: str, result, data_sources: List[str]) -> xr.Dataset:
        # Remove the existing output directory
        filename_parts = [method_name] + data_sources
        filename = "_".join(filename_parts) + "_output.nc"
        output_file = os.path.join(self.output_dir, f"{method_name}", filename)
        logging.info(f"Saving {method_name} output to {output_file}")
        if isinstance(result, xr.DataArray) or isinstance(result, xr.Dataset):
            if isinstance(result, xr.DataArray):
                result = result.to_dataset(name=f"{method_name}")
            result['lat'].attrs['_FillValue'] = float('nan')
            result['lat'].attrs['standard_name'] = 'latitude'
            result['lat'].attrs['long_name'] = 'latitude'
            result['lat'].attrs['units'] = 'degrees_north'
            result['lat'].attrs['axis'] = 'Y'
            result['lon'].attrs['_FillValue'] = float('nan')
            result['lon'].attrs['standard_name'] = 'longitude'
            result['lon'].attrs['long_name'] = 'longitude'
            result['lon'].attrs['units'] = 'degrees_east'
            result['lon'].attrs['axis'] = 'X'
            result.to_netcdf(output_file)
        else:
            # If the result is not xarray object, we might need to handle it differently
            # For now, let's just print it
            logging.info(f"Result of {method_name}: {result}")


class BasicProcessing(statistics_calculate, BaseDatasetProcessing):
    def __init__(self, info):
        """
        Initialize the Statistics class.

        Args:
            info (dict): A dictionary containing additional information to be added as attributes.
        """
        self.name = 'statistics'
        self.version = '0.2'
        self.release = '0.2'
        self.date = 'Mar 2024'
        self.author = "Zhongwang Wei"
        self.__dict__.update(info)

    def check_time_freq(self, time_freq: str) -> xr.Dataset:
        if not [time_freq][0].isdigit():
            time_freq = f'1{time_freq}'
        match = re.match(r'(\d+)\s*([a-zA-Z]+)', time_freq)
        if match:
            num_value, unit = match.groups()
            num_value = int(num_value) if num_value else 1
            unit = self.freq_map.get(unit.lower())
            time_freq = f'{num_value}{unit}'
        else:
            raise ValueError(f"Invalid time resolution format: {time_freq}. Use '3month', '6hr', etc.")
        return time_freq

    def process_data_source(self, source: str, config: Dict[str, Any]) -> xr.Dataset:
        source_config = {k: v for k, v in config.items() if k.startswith(source)}
        dirx = source_config[f'{source}_dir']
        syear = int(source_config[f'{source}_syear'])
        eyear = int(source_config[f'{source}_eyear'])
        time_freq = source_config[f'{source}_tim_res']
        time_freq = self.check_time_freq(time_freq)
        varname = source_config[f'{source}_varname']
        groupby = source_config[f'{source}_data_groupby'].lower()
        suffix = source_config[f'{source}_suffix']
        prefix = source_config[f'{source}_prefix']
        logging.info(f"Processing data source '{source}' from '{dirx}'...")

        if groupby == 'single':
            ds = self.process_single_groupby(dirx, suffix, prefix, varname, syear, eyear, time_freq)
        elif groupby == 'year':
            years = range(syear, eyear + 1)
            ds_list = Parallel(n_jobs=self.num_cores)(
                delayed(self.process_yearly_groupby)(dirx, suffix, prefix, varname, year, year, time_freq)
                for year in years
            )
            ds = xr.concat(ds_list, dim='time')
        else:
            logging.info(f"Combining data to one file...")
            years = range(syear, eyear + 1)
            ds_list = Parallel(n_jobs=self.num_cores)(
                delayed(self.process_other_groupby)(dirx, suffix, prefix, varname, year, year, time_freq)
                for year in years
            )
            ds = xr.concat(ds_list, dim='time')
        ds = Convert_Type.convert_nc(ds)
        return ds

    def process_single_groupby(self, dirx: str, suffix: str, prefix: str, varname: List[str], syear: int, eyear: int,
                               time_freq: str) -> xr.Dataset:
        VarFile = self.check_file_exist(os.path.join(dirx, f'{prefix}{suffix}.nc'))
        if isinstance(varname, str): varname = [varname]
        ds = self.select_var(syear, eyear, time_freq, VarFile, varname, 'stat')
        ds = self.load_and_process_dataset(ds, syear, eyear, time_freq)
        return ds

    def process_yearly_groupby(self, dirx: str, suffix: str, prefix, varname: List[str], syear: int, eyear: int,
                               time_freq: str) -> xr.Dataset:
        VarFile = self.check_file_exist(os.path.join(dirx, f'{prefix}{syear}{suffix}.nc'))
        if isinstance(varname, str): varname = [varname]
        ds = self.select_var(syear, eyear, time_freq, VarFile, varname, 'stat')
        ds = self.load_and_process_dataset(ds, syear, eyear, time_freq)
        return ds

    def process_other_groupby(self, dirx: str, suffix: str, prefix: str, varname: List[str], syear: int, eyear: int,
                              time_freq: str) -> xr.Dataset:
        if isinstance(varname, str): varname = [varname]
        ds = self.combine_year(syear, dirx, dirx, suffix, prefix, varname, 'stat', time_freq)
        ds = self.load_and_process_dataset(ds, syear, eyear, time_freq)
        return ds

    def load_and_process_dataset(self, ds: xr.Dataset, syear: str, eyear: str, time_freq) -> xr.Dataset:
        ds = self.check_coordinate(ds)
        ds = self.check_dataset_time_integrity(ds, syear, eyear, time_freq, 'stat')
        ds = self.select_timerange(ds, syear, eyear)
        return ds

    def remap_data(self, data_list):
        """
        Remap all datasets to the resolution specified in main.nml.
        Tries CDO first, then xESMF, and finally xarray's interp method.
        """

        remapping_methods = [
            self.remap_interpolate,
            self.remap_xesmf,
            self.remap_cdo
        ]

        remapped_data = []
        for i, data in enumerate(data_list):
            data = self.preprocess_grid_data(data)
            new_grid = self.create_target_grid()
            for method in remapping_methods:
                try:
                    remapped = method(data, new_grid)
                except Exception as e:
                    logging.warning(f"{method.__name__} failed: {e}")

            remapped = remapped.resample(time=self.compare_tim_res).mean()
            remapped_data.append(remapped)
        return remapped_data

    def preprocess_grid_data(self, data: xr.Dataset) -> xr.Dataset:
        # Check if lon and lat are 2D
        data = self.check_coordinate(data)
        if data['lon'].ndim == 2 and data['lat'].ndim == 2:
            try:
                data = convert_to_wgs84_xesmf(data, self.compare_grid_res)
            except:
                data = convert_to_wgs84_scipy(data, self.compare_grid_res)

        # Convert longitude values
        lon = data['lon'].values
        lon_adjusted = np.where(lon > 180, lon - 360, lon)

        # Create a new DataArray with adjusted longitude values
        new_lon = xr.DataArray(lon_adjusted, dims='lon', attrs=data['lon'].attrs)

        # Assign the new longitude to the dataset
        data = data.assign_coords(lon=new_lon)

        # If needed, sort the dataset by the new longitude values
        data = data.sortby('lon')

        return data

    def create_target_grid(self) -> xr.Dataset:
        min_lon = self.main_nml['general']['min_lon']
        min_lat = self.main_nml['general']['min_lat']
        max_lon = self.main_nml['general']['max_lon']
        max_lat = self.main_nml['general']['max_lat']
        lon_new = np.arange(min_lon + self.compare_grid_res / 2, max_lon, self.compare_grid_res)
        lat_new = np.arange(min_lat + self.compare_grid_res / 2, max_lat, self.compare_grid_res)
        return xr.Dataset({'lon': lon_new, 'lat': lat_new})

    def remap_interpolate(self, data: xr.Dataset, new_grid: xr.Dataset) -> xr.DataArray:
        from regrid import Grid
        min_lon = self.main_nml['general']['min_lon']
        min_lat = self.main_nml['general']['min_lat']
        max_lon = self.main_nml['general']['max_lon']
        max_lat = self.main_nml['general']['max_lat']

        grid = Grid(
            north=max_lat - self.compare_grid_res / 2,
            south=min_lat + self.compare_grid_res / 2,
            west=min_lon + self.compare_grid_res / 2,
            east=max_lon - self.compare_grid_res / 2,
            resolution_lat=self.compare_grid_res,
            resolution_lon=self.compare_grid_res,
        )
        target_dataset = grid.create_regridding_dataset(lat_name="lat", lon_name="lon")
        # Convert sparse arrays to dense arrays
        data_regrid = data.regrid.conservative(target_dataset, nan_threshold=0)
        return Convert_Type.convert_nc(data_regrid)

    def remap_xesmf(self, data: xr.Dataset, new_grid: xr.Dataset) -> xr.DataArray:
        import xesmf as xe
        regridder = xe.Regridder(data, new_grid, 'conservative')
        ds = regridder(data)
        return list(Convert_Type.convert_nc(ds.data_vars).values())[0]

    def remap_cdo(self, data: xr.Dataset, new_grid: xr.Dataset) -> xr.DataArray:
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.nc') as temp_input, \
                tempfile.NamedTemporaryFile(suffix='.nc') as temp_output, \
                tempfile.NamedTemporaryFile(suffix='.txt') as temp_grid:
            data.to_netcdf(temp_input.name)
            self.create_target_grid_file(temp_grid.name, new_grid)

            cmd = f"cdo -s remapcon,{temp_grid.name} {temp_input.name} {temp_output.name}"
            subprocess.run(cmd, shell=True, check=True)
            ds = xr.open_dataset(temp_output.name)
            return list(Convert_Type.convert_nc(ds.data_vars).values())[0]

    def create_target_grid_file(self, filename: str, new_grid: xr.Dataset) -> None:
        min_lon = self.main_nml['general']['min_lon']
        min_lat = self.main_nml['general']['min_lat']
        with open(filename, 'w') as f:
            f.write(f"gridtype = lonlat\n")
            f.write(f"xsize = {len(new_grid.lon)}\n")
            f.write(f"ysize = {len(new_grid.lat)}\n")
            f.write(f"xfirst = {min_lon + self.compare_grid_res / 2}\n")
            f.write(f"xinc = {self.compare_grid_res}\n")
            f.write(f"yfirst = {min_lat + self.compare_grid_res / 2}\n")
            f.write(f"yinc = {self.compare_grid_res}\n")

    def save_result(self, method_name: str, result, data_sources: List[str]) -> xr.Dataset:
        # Remove the existing output directory
        filename_parts = [method_name] + data_sources
        filename = "_".join(filename_parts) + "_output.nc"
        output_file = os.path.join(self.output_dir, f"{method_name}", filename)
        logging.info(f"Saving {method_name} output to {output_file}")
        if isinstance(result, xr.DataArray) or isinstance(result, xr.Dataset):
            if isinstance(result, xr.DataArray):
                result = result.to_dataset(name=f"{method_name}")
            else:
                if method_name in ['Mean', 'Median', 'Max', 'Min', 'Sum']:
                    if method_name not in result.data_vars:
                        varname = next(iter(result.data_vars))
                        result = result.rename({varname: method_name})
            result['lat'].attrs['_FillValue'] = float('nan')
            result['lat'].attrs['standard_name'] = 'latitude'
            result['lat'].attrs['long_name'] = 'latitude'
            result['lat'].attrs['units'] = 'degrees_north'
            result['lat'].attrs['axis'] = 'Y'
            result['lon'].attrs['_FillValue'] = float('nan')
            result['lon'].attrs['standard_name'] = 'longitude'
            result['lon'].attrs['long_name'] = 'longitude'
            result['lon'].attrs['units'] = 'degrees_east'
            result['lon'].attrs['axis'] = 'X'
            result.to_netcdf(output_file)
        else:
            # If the result is not xarray object, we might need to handle it differently
            # For now, let's just print it
            logging.info(f"Result of {method_name}: {result}")
        return output_file

    coordinate_map = {
        'longitude': 'lon', 'long': 'lon', 'lon_cama': 'lon', 'lon0': 'lon', 'x': 'lon',
        'latitude': 'lat', 'lat_cama': 'lat', 'lat0': 'lat', 'y': 'lat',
        'Time': 'time', 'TIME': 'time', 't': 'time', 'T': 'time',
        'elevation': 'elev', 'height': 'elev', 'z': 'elev', 'Z': 'elev',
        'h': 'elev', 'H': 'elev', 'ELEV': 'elev', 'HEIGHT': 'elev',
    }
    freq_map = {
        'month': 'ME',
        'mon': 'ME',
        'monthly': 'ME',
        'day': 'D',
        'daily': 'D',
        'hour': 'H',
        'Hour': 'H',
        'hr': 'H',
        'Hr': 'H',
        'h': 'H',
        'hourly': 'H',
        'year': 'Y',
        'yr': 'Y',
        'yearly': 'Y',
        'week': 'W',
        'wk': 'W',
        'weekly': 'W',
    }


class StatisticsProcessing(BasicProcessing):
    def __init__(self, main_nml, stats_nml, output_dir, num_cores=-1):
        super().__init__(main_nml)
        super().__init__(stats_nml)
        self.name = 'StatisticsDataHandler'
        self.version = '0.3'
        self.release = '0.3'
        self.date = 'June 2024'
        self.author = "Zhongwang Wei"

        self.stats_nml = stats_nml
        self.main_nml = main_nml
        self.general_config = self.stats_nml['general']
        self.output_dir = output_dir
        self.num_cores = num_cores

        # Extract remapping information from main namelist
        self.compare_grid_res = self.main_nml['general']['compare_grid_res']
        self.compare_tim_res = self.main_nml['general'].get('compare_tim_res', '1').lower()

        # this should be done in read_namelist
        # adjust the time frequency
        match = re.match(r'(\d*)\s*([a-zA-Z]+)', self.compare_tim_res)
        if not match:
            logging.error("Invalid time resolution format. Use '3month', '6hr', etc.")
            raise ValueError("Invalid time resolution format. Use '3month', '6hr', etc.")
        value, unit = match.groups()
        if not value:
            value = 1
        else:
            value = int(value)  # Convert the numerical value to an integer
        # Get the corresponding pandas frequency
        freq = self.freq_map.get(unit.lower())
        if not freq:
            logging.error(f"Unsupported time unit: {unit}")
            raise ValueError(f"Unsupported time unit: {unit}")
        self.compare_tim_res = f'{value}{freq}'

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def setup_output_directories(self, statistic_method):
        if os.path.exists(os.path.join(self.output_dir, f"{statistic_method}")):
            shutil.rmtree(os.path.join(self.output_dir, f"{statistic_method}"))
        # Create a new output directory
        if not os.path.exists(os.path.join(self.output_dir, f"{statistic_method}")):
            os.makedirs(os.path.join(self.output_dir, f"{statistic_method}"))

    # Basic statistical methods
    def scenarios_Basic_analysis(self, statistic_method, statistic_nml, option):
        self.setup_output_directories(statistic_method)
        logging.info(f"Processing {statistic_method}")
        # Load data sources for this method
        data_sources_key = f'{statistic_method}_data_source'
        if data_sources_key not in self.general_config:
            logging.warning(f"Warning: No data sources found for '{statistic_method}' in stats.nml [general] section.")
            return

            # Assuming 'statistic_method' is defined and corresponds to one of the keys in the configuration
        data_source_config = self.general_config.get(f'{statistic_method}_data_source', '')

        # Check if the data_source_config is a string; if not, handle it appropriately
        if isinstance(data_source_config, str):
            data_sources = data_source_config.split(',')
        else:
            # Assuming data_source_config is a list or another iterable; adjust as necessary
            data_sources = data_source_config  # If it's already a list, no need to split
        for source in data_sources:
            sources = [source.strip()]
            output_file = self.run_analysis(source.strip(), sources, statistic_method)
            make_Basic(output_file, statistic_method, [source], self.main_nml['general'], option)

    def scenarios_Mann_Kendall_Trend_Test_analysis(self, statistic_method, statistic_nml, option):
        self.setup_output_directories(statistic_method)
        # Load data sources for this method
        data_sources_key = f'{statistic_method}_data_source'
        if data_sources_key not in self.general_config:
            logging.warning(f"Warning: No data sources found for '{statistic_method}' in stats.nml [general] section.")
            return

            # Assuming 'statistic_method' is defined and corresponds to one of the keys in the configuration
        data_source_config = self.general_config.get(f'{statistic_method}_data_source', '')

        # Check if the data_source_config is a string; if not, handle it appropriately
        if isinstance(data_source_config, str):
            data_sources = data_source_config.split(',')
        else:
            # Assuming data_source_config is a list or another iterable; adjust as necessary
            data_sources = data_source_config  # If it's already a list, no need to split
        for source in data_sources:
            option['significance_level'] = statistic_nml['significance_level']
            sources = [source.strip()]
            output_file = self.run_analysis(source.strip(), sources, statistic_method)
            make_Mann_Kendall_Trend_Test(output_file, statistic_method, [source], self.main_nml['general'], option)

    def scenarios_Correlation_analysis(self, statistic_method, statistic_nml, option):
        self.setup_output_directories(statistic_method)

        # Load data sources for this method
        data_sources_key = f'{statistic_method}_data_source'
        if data_sources_key not in self.general_config:
            logging.warning(f"Warning: No data sources found for '{statistic_method}' in stats.nml [general] section.")
            return

            # Assuming 'statistic_method' is defined and corresponds to one of the keys in the configuration
        data_source_config = self.general_config.get(f'{statistic_method}_data_source', '')

        # Check if the data_source_config is a string; if not, handle it appropriately
        if isinstance(data_source_config, str):
            data_sources = data_source_config.split(',')
        else:
            # Assuming data_source_config is a list or another iterable; adjust as necessary
            data_sources = data_source_config  # If it's already a list, no need to split
        for source in data_sources:
            sources = [f'{source}1', f'{source}2']
            output_file = self.run_analysis(source.strip(), sources, statistic_method)
            make_Correlation(output_file, statistic_method, self.main_nml['general'], option)

    def scenarios_Standard_Deviation_analysis(self, statistic_method, statistic_nml, option):
        self.setup_output_directories(statistic_method)
        # Load data sources for this method
        data_sources_key = f'{statistic_method}_data_source'
        if data_sources_key not in self.general_config:
            logging.warning(f"Warning: No data sources found for '{statistic_method}' in stats.nml [general] section.")
            return

            # Assuming 'statistic_method' is defined and corresponds to one of the keys in the configuration
        data_source_config = self.general_config.get(f'{statistic_method}_data_source', '')

        # Check if the data_source_config is a string; if not, handle it appropriately
        if isinstance(data_source_config, str):
            data_sources = data_source_config.split(',')
        else:
            # Assuming data_source_config is a list or another iterable; adjust as necessary
            data_sources = data_source_config  # If it's already a list, no need to split
        for source in data_sources:
            sources = [source.strip()]
            output_file = self.run_analysis(source.strip(), sources, statistic_method)
            make_Standard_Deviation(output_file, statistic_method, [source], self.main_nml['general'], option)

    def scenarios_Hellinger_Distance_analysis(self, statistic_method, statistic_nml, option):
        self.setup_output_directories(statistic_method)

        # Load data sources for this method
        data_sources_key = f'{statistic_method}_data_source'
        if data_sources_key not in self.general_config:
            logging.warning(f"Warning: No data sources found for '{statistic_method}' in stats.nml [general] section.")
            return

            # Assuming 'statistic_method' is defined and corresponds to one of the keys in the configuration
        data_source_config = self.general_config.get(f'{statistic_method}_data_source', '')

        # Check if the data_source_config is a string; if not, handle it appropriately
        if isinstance(data_source_config, str):
            data_sources = data_source_config.split(',')
        else:
            # Assuming data_source_config is a list or another iterable; adjust as necessary
            data_sources = data_source_config  # If it's already a list, no need to split
        for source in data_sources:
            sources = [f'{source}1', f'{source}2']
            output_file = self.run_analysis(source.strip(), sources, statistic_method)
            make_Hellinger_Distance(output_file, statistic_method, [source], self.main_nml['general'], option)

    def scenarios_Z_Score_analysis(self, statistic_method, statistic_nml, option):
        self.setup_output_directories(statistic_method)
        # Load data sources for this method
        data_sources_key = f'{statistic_method}_data_source'
        if data_sources_key not in self.general_config:
            logging.warning(f"Warning: No data sources found for '{statistic_method}' in stats.nml [general] section.")
            return

            # Assuming 'statistic_method' is defined and corresponds to one of the keys in the configuration
        data_source_config = self.general_config.get(f'{statistic_method}_data_source', '')

        # Check if the data_source_config is a string; if not, handle it appropriately
        if isinstance(data_source_config, str):
            data_sources = data_source_config.split(',')
        else:
            # Assuming data_source_config is a list or another iterable; adjust as necessary
            data_sources = data_source_config  # If it's already a list, no need to split
        for source in data_sources:
            sources = [source.strip()]
            output_file = self.run_analysis(source.strip(), sources, statistic_method)
            # make_Z_Score(output_file, statistic_method, [source], self.main_nml['general'], statistic_nml, option)

    def scenarios_Three_Cornered_Hat_analysis(self, statistic_method, statistic_nml, option):
        self.setup_output_directories(statistic_method)
        # Load data sources for this method
        data_sources_key = f'{statistic_method}_data_source'
        if data_sources_key not in self.general_config:
            logging.warning(f"Warning: No data sources found for '{statistic_method}' in stats.nml [general] section.")
            return

            # Assuming 'statistic_method' is defined and corresponds to one of the keys in the configuration
        data_source_config = self.general_config.get(f'{statistic_method}_data_source', '')

        # Check if the data_source_config is a string; if not, handle it appropriately
        if isinstance(data_source_config, str):
            data_sources = data_source_config.split(',')
        else:
            # Assuming data_source_config is a list or another iterable; adjust as necessary
            data_sources = data_source_config  # If it's already a list, no need to split
        for source in data_sources:
            nX = int(statistic_nml[f'{source}_nX'])
            if nX < 3:
                logging.error('Error: Three Cornered Hat method must be at least 3 dataset.')
                exit(1)
            sources = [f'{source}{i}' for i in range(1, nX + 1)]
            output_file = self.run_analysis(source.strip(), sources, statistic_method)
            make_Three_Cornered_Hat(output_file, statistic_method, [source],self.main_nml['general'],  statistic_nml, option)

    def scenarios_Partial_Least_Squares_Regression_analysis(self, statistic_method, statistic_nml, option):
        self.setup_output_directories(statistic_method)

        # Load data sources for this method
        data_sources_key = f'{statistic_method}_data_source'
        if data_sources_key not in self.general_config:
            logging.warning(f"Warning: No data sources found for '{statistic_method}' in stats.nml [general] section.")
            return

            # Assuming 'statistic_method' is defined and corresponds to one of the keys in the configuration
        data_source_config = self.general_config.get(f'{statistic_method}_data_source', '')

        # Check if the data_source_config is a string; if not, handle it appropriately
        if isinstance(data_source_config, str):
            data_sources = data_source_config.split(',')
        else:
            # Assuming data_source_config is a list or another iterable; adjust as necessary
            data_sources = data_source_config  # If it's already a list, no need to split
        for source in data_sources:
            nX = int(statistic_nml[f'{source}_nX'])
            sources = [f'{source}_Y'] + [f'{source}_X{i + 1}' for i in range(nX)]
            output_file = self.run_analysis(source.strip(), sources, statistic_method)
            make_Partial_Least_Squares_Regression(output_file, statistic_method, [source], self.main_nml['general'],
                                                  statistic_nml, option)

    # Advanced statistical methods
    def scenarios_Functional_Response_analysis(self, statistic_method, statistic_nml, option):
        self.setup_output_directories(statistic_method)
        # Load data sources for this method
        data_sources_key = f'{statistic_method}_data_source'
        if data_sources_key not in self.general_config:
            logging.warning(f"Warning: No data sources found for '{statistic_method}' in stats.nml [general] section.")
            return

            # Assuming 'statistic_method' is defined and corresponds to one of the keys in the configuration
        data_source_config = self.general_config.get(f'{statistic_method}_data_source', '')

        # Check if the data_source_config is a string; if not, handle it appropriately
        if isinstance(data_source_config, str):
            data_sources = data_source_config.split(',')
        else:
            # Assuming data_source_config is a list or another iterable; adjust as necessary
            data_sources = data_source_config  # If it's already a list, no need to split
        for source in data_sources:
            sources = [f'{source}1', f'{source}2']
            output_file = self.run_analysis(source.strip(), sources, statistic_method)
            make_Functional_Response(output_file, statistic_method, [source], self.main_nml['general'], option)

    def scenarios_False_Discovery_Rate_analysis(self, statistic_method, statistic_nml, option):
        return

    def scenarios_ANOVA_analysis(self, statistic_method, statistic_nml, option):
        self.setup_output_directories(statistic_method)
        # Load data sources for this method
        data_sources_key = f'{statistic_method}_data_source'
        if data_sources_key not in self.general_config:
            logging.warning(f"Warning: No data sources found for '{statistic_method}' in stats.nml [general] section.")
            return

            # Assuming 'statistic_method' is defined and corresponds to one of the keys in the configuration
        data_source_config = self.general_config.get(f'{statistic_method}_data_source', '')

        # Check if the data_source_config is a string; if not, handle it appropriately
        if isinstance(data_source_config, str):
            data_sources = data_source_config.split(',')
        else:
            # Assuming data_source_config is a list or another iterable; adjust as necessary
            data_sources = data_source_config  # If it's already a list, no need to split
        for source in data_sources:
            sources = [f'{source}_Y', f'{source}_X']
            output_file = self.run_analysis(source.strip(), sources, statistic_method)
            make_ANOVA(output_file, statistic_method, [source], self.main_nml['general'], statistic_nml, option)

    def run_analysis(self, source: str, sources: List[str], statistic_method):
        method_function = getattr(self, f"stat_{statistic_method.lower()}", None)
        if method_function:
            data_list = [self.process_data_source(isource.strip(), self.stats_nml[statistic_method])
                         for isource in sources]

            if statistic_method == 'Partial_Least_Squares_Regression':
                try:
                    Y_vars = self.process_data_source(sources[0].strip(), self.stats_nml[statistic_method])
                except:
                    logging.error("No dependent variable (Y) found. Ensure at least one variable has '_Y_' in its name.")
                    raise ValueError(
                        "No dependent variable (Y) found. Ensure at least one variable has '_Y_' in its name.")

            if len(data_list) == 0:
                logging.error(f"Warning: No data sources found for '{statistic_method}'.")
                exit()
            # Remap data
            data_list = self.remap_data(data_list)

            # Call the method with the loaded data
            result = method_function(*data_list)
            output_file = self.save_result(statistic_method, result, [source])
            return output_file
        else:
            logging.warning(f"Warning: Analysis method '{statistic_method}' not implemented.")
