"""The Sampling configuration file consists of the parameters which conducting adaptive sampling/active learning from the VRM system 
                
        :param sampling_config['sample_dim']: Initial set (number) of KCC values to be generated to be sent to VRM for deviation pattern simulation
        :type sampling_config['sample_dim']: int (required)

        :param sampling_config['adaptive_sample_dim']: Consecutive adaptive set (number) of KCC values to be generated to be sent to VRM for deviation pattern simulation
        :type sampling_config['adaptive_sample_dim']: int (required)

        :param sampling_config['adaptive_runs']: Number of adaptive runs to conducted used as a terminating criteria for active learning
        :type sampling_config['adaptive_runs']: int (required)

        :param sampling_config['sample_type']: Initial sampling strategy uniform or LHS (Latin Hypercube Sampling), defaults to LHS
        :type sampling_config['sample_type']: str (required)

        :param sampling_config['sample_type']: The output filename of the generated samples to be used as input for the VRM software
        :type sampling_config['sample_type']: str (required)

"""

sampling_config={'sample_dim':3000,
		'adaptive_sample_dim':2000,
		'adaptive_runs':5,	
        'sample_type':'lhs',
        'output_file_name':'inner_rf_samples_train_set.csv'
        }