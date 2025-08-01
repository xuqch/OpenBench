import logging
class UnitProcessing:
	def __init__(self, info):
		self.name = 'plotting'
		self.version = '0.1'
		self.release = '0.1'
		self.date = 'Mar 2023'
		self.author = "Zhongwang Wei / zhongwang007@gmail.com"
		self.__dict__.update(info)

	@staticmethod
	def convert_unit(data, input_unit):
		"""
		Generic unit conversion method.
		Converts input unit to the base unit if possible.
		If data is None, only returns the converted unit without data conversion.
		"""
		conversion_factors = {
			'g m-2 day-1': {
				'mol m-2 s-1': lambda x: x * (86400 * 12.01),
				'gc m-2 s-1': lambda x: x * 86400,
				'g m-2 s-1': lambda x: x * 86400,
				'mumolco2 m-2 s-1': lambda x: x * (12e-6 * 86400),
				'mumolCO2 m-2 s-1': lambda x: x * (12e-6 * 86400),
			},
			'mm day-1': {
				'kg m-2 s-1': lambda x: x * 86400,
				'mm s-1': lambda x: x * 86400,
				'mm hr-1': lambda x: x * 24,
				'mm h-1': lambda x: x * 24,
				'mm hour-1': lambda x: x * 24,
				'mm mon-1': lambda x: x / 30.44,
				'mm m-1': lambda x: x / 30.44,
				'mm month-1': lambda x: x / 30.44,
				'w m-2 heat': lambda x: x /28.4,
				'mm 3hour-1': lambda x: x * 8,
			},

			'w m-2': {
				'mj m-2 day-1': lambda x: x * 11.574074074074074,  # 1 / 0.0864
				'mj m-2 d-1': lambda x: x * 11.574074074074074,  # 1 / 0.0864
			},
			'unitless': {
				'percent': lambda x: x / 100,
				'percentage': lambda x: x / 100,
				'%': lambda x: x / 100,
				'g kg-1': lambda x: x / 1000,
				'fraction': lambda x: x,
				'm3 m-3': lambda x: x,
				'm2 m-2': lambda x: x,
				'g g-1': lambda x: x,
			},
			'k': {
				'c': lambda x: x + 273.15,
				'f': lambda x: (x - 32) * 5 / 9 + 273.15,
			},
			'm3 s-1': {
				'm3 day-1': lambda x: x / 86400,
				'm3 d-1': lambda x: x / 86400,
				'L s-1': lambda x: x * 1000,
			},
			'mcm': {
				'm3': lambda x: x * 1e6,
				'km3': lambda x: x / 1000,
				'million cubic meters': lambda x: x,
			},
			'mm year-1': {
				'm year-1': lambda x: x / 1000,
				'cm year-1': lambda x: x / 10,
				'kg m-2': lambda x: x,
				'mm month-1': lambda x: x * 12,
				'mm mon-1': lambda x: x * 12,
				'mm day-1': lambda x: x * 365,
			},
			'm': {
				'cm': lambda x: x / 100,
				'mm': lambda x: x / 1000,
			},
			'km2': {
				'm2': lambda x: x / 1.e6,
			},

			'm s-1': {
				'km h-1': lambda x: x * 3.6,
			},
			't ha-1': {
				'kg ha-1': lambda x: x / 1000,
			},
			'kg c m-2': {
				'g c m-2': lambda x: x / 1000,
			},
		}
		logging.info(f'Converting {input_unit} to base unit...')
		
		# Normalize input unit for case-insensitive comparison
		input_unit_lower = input_unit.lower()
		
		for base_unit, conversions in conversion_factors.items():
			# Check if input unit matches base unit (case-insensitive)
			if input_unit_lower == base_unit.lower():
				logging.info(f'No conversion needed for {input_unit}')
				return data, base_unit

			# Check conversions (case-insensitive)
			for conv_unit, conv_func in conversions.items():
				if input_unit_lower == conv_unit.lower():
					# If data is None, only return the target unit
					if data is None:
						logging.info(f'Unit mapping found: {input_unit} -> {base_unit}')
						return None, base_unit
					else:
						converted_data = conv_func(data)
						logging.info(f'Successfully converted {input_unit} to {base_unit}')
						return converted_data, base_unit
		
		# If no conversion is found after checking all base units
		logging.warning(f'No conversion found for {input_unit}. Using original data and unit.')
		return data, input_unit  # Return original data instead of raising error

	@staticmethod
	def process_unit(self, data, unit):
		"""
		Process unit conversion for a specific item.
		"""
		if hasattr(UnitProcessing, f'Unit_{self.item}'):
			return getattr(UnitProcessing, f'Unit_{self.item}')(self, data, unit)
		else:
			logging.error(f"Unit conversion for {self.item} is not supported!")
			raise ValueError(f"Unit conversion for {self.item} is not supported!")

	@staticmethod
	def check_units(input_units, target_units):
		"""
		Check if input units match target units.
		"""
		return sorted(input_units.lower().split()) == sorted(target_units.lower().split())
