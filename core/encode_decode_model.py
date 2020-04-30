
class Encode_Decode_Model:    
	""" Deep Learning Model Class

		:param model_type: Type of model to be used for training 3D CNN with MSE loss, 3D CNN with hetreoskedastic aleatoric loss, 3D CNN with a mixture density network (GMM) output
		:type model_type: str (required)

		:param output_dimension: Number of output nodes for the network equal to number of KCCs for the assembly in case MSE is used as loss function
		:type output_dimension: int (required)

		:param optimizer: The optimizer to be used while model training, refer: https://keras.io/optimizers/ for more information
		:type optimizer: keras.optimizer (required) 

		:param loss_function: The loss function to be optimized by training the model, refer: https://keras.io/losses/ for more information
		:type loss_function: keras.losses (required)

		:param regularizer_coeff: The L2 norm regularization coefficient value used in the penultimate fully connected layer of the model, refer: https://keras.io/regularizers/ for more information
		:type regularizer_coeff: float (required)

		:param output_type: The output type of the model which can be regression or classification, this is used to define the output layer of the model, defaults to regression (classification: softmax, regression: linear)
		:type output_type: str      

	"""
	def __init__(self,output_dimension):
		
		self.output_dimension=output_dimension


	def encode_decode_3d(self,filter_root, depth,input_size=(64,64,64,3), n_class=3):
		"""Build the 3D Model using the specified loss function, the inputs are parsed from the assemblyconfig_<case_study_name>.py file

			:param voxel_dim: The voxel dimension of the input, required to build input to the 3D CNN model
			:type voxel_dim: int (required)

			:param voxel_channels: The number of voxel channels in the input structure, required to build input to the 3D CNN model
			:type voxel_channels: int (required)
		"""

		import tensorflow as tf
		import tensorflow_probability as tfp
		import numpy as np
		tfd = tfp.distributions
		
		import tensorflow.keras.backend as K 
		from tensorflow.keras.models import Model
		from tensorflow.keras.layers import Conv3D, MaxPooling3D, Add, BatchNormalization, Input, Activation, Lambda, Concatenate, Flatten, Dense,UpSampling3D,GlobalAveragePooling3D
		from tensorflow.keras.utils import plot_model
		
		"""
		Build UNet model with ResBlock.
		Args:
			filter_root (int): Number of filters to start with in first convolution.
			depth (int): How deep to go in UNet i.e. how many down and up sampling you want to do in the model. 
						Filter root and image size should be multiple of 2^depth.
			n_class (int, optional): How many classes in the output layer. Defaults to 2.
			input_size (tuple, optional): Input image size. Defaults to (256, 256, 1).
			activation (str, optional): activation to use in each convolution. Defaults to 'relu'.
			batch_norm (bool, optional): To use Batch normaliztion or not. Defaults to True.
			final_activation (str, optional): activation for output layer. Defaults to 'softmax'.
		Returns:
			obj: keras model object
		"""
		inputs = Input(input_size)
		x = inputs
		
		# Dictionary for long connections to Up Sampling Layers
		long_connection_store = {}

		Conv = Conv3D
		MaxPooling = MaxPooling3D
		UpSampling = UpSampling3D
		
		activation='relu'
		final_activation='linear'

		# Down sampling
		for i in range(depth):
			out_channel = 2**i * filter_root

			# Residual/Skip connection
			res = Conv(out_channel, kernel_size=1, padding='same', use_bias=False, name="Identity{}_1".format(i))(x)

			# First Conv Block with Conv, BN and activation
			conv1 = Conv(out_channel, kernel_size=3, padding='same', name="Conv{}_1".format(i))(x)
			#if batch_norm:
				#conv1 = BatchNormalization(name="BN{}_1".format(i))(conv1)
			act1 = Activation(activation, name="Act{}_1".format(i))(conv1)

			# Second Conv block with Conv and BN only
			conv2 = Conv(out_channel, kernel_size=3, padding='same', name="Conv{}_2".format(i))(act1)
			#if batch_norm:
				#conv2 = BatchNormalization(name="BN{}_2".format(i))(conv2)

			resconnection = Add(name="Add{}_1".format(i))([res, conv2])

			act2 = Activation(activation, name="Act{}_2".format(i))(resconnection)

			# Max pooling
			if i < depth - 1:
				long_connection_store[str(i)] = act2
				x = MaxPooling(padding='same', name="MaxPooling{}_1".format(i))(act2)
			else:
				x = act2

		feature_vector=Conv(self.output_dimension, 1, padding='same', activation=final_activation, name='Process_Parameter_output')(x)
		process_parameter=GlobalAveragePooling3D()(feature_vector)
		
		#feature_vector=Flatten()(x)
		#process_parameter=Dense(self.output_dimension)(feature_vector)
		
		# Upsampling
		for i in range(depth - 2, -1, -1):
			out_channel = 2**(i) * filter_root

			# long connection from down sampling path.
			long_connection = long_connection_store[str(i)]

			up1 = UpSampling(name="UpSampling{}_1".format(i))(x)
			up_conv1 = Conv(out_channel, 2, activation='relu', padding='same', name="upConvSam{}_1".format(i))(up1)

			#  Concatenate.
			up_conc = Concatenate(axis=-1, name="upConcatenate{}_1".format(i))([up_conv1, long_connection])

			#  Convolutions
			up_conv2 = Conv(out_channel, 3, padding='same', name="upConv{}_1".format(i))(up_conc)

			up_act1 = Activation(activation, name="upAct{}_1".format(i))(up_conv2)

			up_conv2 = Conv(out_channel, 3, padding='same', name="upConv{}_2".format(i))(up_act1)

			# Residual/Skip connection
			res = Conv(out_channel, kernel_size=1, padding='same', use_bias=False, name="upIdentity{}_1".format(i))(up_conc)

			resconnection = Add(name="upAdd{}_1".format(i))([res, up_conv2])

			x = Activation(activation, name="upAct{}_2".format(i))(resconnection)

		# Final convolution
		output = Conv(n_class, 1, padding='same', activation=final_activation, name='output')(x)

		model=Model(inputs, outputs=[process_parameter,output], name='Res-UNet')
		
		print("U-Net Based 3D Encoder Decoder Model Compiled")
		#print(model.summary())
		#plot_model(model,to_file='unet_3D.png',show_shapes=True, show_layer_names=True)
		
		
		mse_basic = tf.keras.losses.MeanSquaredError()
		msle = tf.keras.losses.MeanSquaredLogarithmicError()
		
		def mse_scaled(y_true,y_pred):
			return K.mean(K.square((y_pred - y_true)/10))

		model.compile(optimizer=tf.keras.optimizers.Adam(),experimental_run_tf_function=False,loss=[tf.keras.losses.MeanSquaredError(),mse_scaled],metrics=[tf.keras.losses.MeanSquaredError(),mse_scaled,msle,tf.keras.metrics.MeanAbsoluteError()])
		#print(model.summary())
		return model

if (__name__=="__main__"):
	
	print('Model Summary')
	enc_dec=Encode_Decode_Model(6)

	model=enc_dec.encode_decode_3d(32,4)