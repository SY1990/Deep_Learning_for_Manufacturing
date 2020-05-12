""" Feature importance of ensemble models such as Gradient Boosted Trees or Random Forests is used in determining KMCs for each KCC
"""

import os
import sys
current_path=os.path.dirname(__file__)
parentdir = os.path.dirname(current_path)

#Adding Path to various Modules
sys.path.append("../core")
sys.path.append("../visualization")
sys.path.append("../utilities")
sys.path.append("../datasets")
sys.path.append("../trained_models")
sys.path.append("../config")


#from sklearn import RandomForestRegressor
import pathlib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn import metrics
import xgboost as xgb
from sklearn.externals import joblib

#Importing Config files
import assembly_config as config
import model_config as cftrain

#Importing required modules from the package
from measurement_system import HexagonWlsScanner
from assembly_system import VRMSimulationModel
from data_import import GetTrainData
import voxel_config as vc
from cop_viz import CopViz


def kmc_model_build(tree_based_model,point_data,selected_kcc,kcc_name,split_ratio=0.2,save_model=0):
	"""kmc_model_build function inputs model_type and data to generate KMC for each KCC

		:param tree_based_model: Type of model to be used for feature importance 
		:type tree_based_model: str (required)

		:param point_data: input data consisting of node deviations
		:type point_data: numpy.array (samples*nodes) (required)

		:param selected_kcc: output data consisting of selected process parameter/KCC
		:type selected_kcc: numpy.array (samples*1) (required)

		:param kcc_name: unique identifier for the KCC
		:type kcc_name: str (required)

		:param split_ratio: test data split
		:type split_ratio: float

		:param save_model: Save model flag, set to 1 to save model
		:type save_model: int

		:returns: filtered_nodeIDs_x, node ids for which x-deviation is significant given the kcc
		:rtype: numpy.array [kmcs*1]

		:returns: filtered_nodeIDs_y, node ids for which y-deviation is significant given the kcc
		:rtype: numpy.array [kmcs*1]

		:returns: filtered_nodeIDs_z, node ids for which z-deviation is significant given the kcc
		:rtype: numpy.array [kmcs*1]
	"""
	train_X, test_X, train_y, test_y = train_test_split(point_data, selected_kcc, test_size = 0.2)
	train=train_X
	target=train_y
	train.index=range(0,train.shape[0])
	target.index=range(0,train.shape[0])
	
	#%%
	print('KMC Generation for selected :', kcc_name)

	if(tree_based_model=='rf'):
		model=RandomForestRegressor(n_estimators=500,max_depth=300,n_jobs=-1,verbose=True)
	
	if(tree_based_model=='xgb'):
		model=xgb.XGBRegressor(colsample_bytree=0.4,gamma=0.045,learning_rate=0.07,max_depth=500,min_child_weight=1.5,n_estimators=150,reg_alpha=0.65,reg_lambda=0.45,subsample=0.95,n_jobs=-1,verbose=True)
	
	model.fit(train,target)
	#%%
	y_pred = model.predict(test_X)

	mae=metrics.mean_absolute_error(test_y, y_pred)
	
	print('The MAE for feature selection for: ',kcc_name)
	print(mae)
	
	if(save_model==1):
		filename = kcc_name+'_XGB_model.sav'
		joblib.dump(model, filename)
		print('Trained Model Saved to disk....')
	
	thresholds = model.feature_importances_
	node_id=np.arange(start=1, stop=point_data.shape[1]+1, step=1)
	threshold_data=np.zeros((point_data.shape[1],2))
	threshold_data[:,0]=node_id
	threshold_data[:,1]=thresholds
	print(point_data.shape[1])
	
	node_IDs = pd.DataFrame(data=threshold_data,columns=['node_id','Feature_Importance'])
	node_IDs = node_IDs.sort_values('Feature_Importance', ascending=False)
	filtered_nodeIDs=node_IDs.loc[node_IDs['Feature_Importance'] >= 0.01]
	
	filtered_nodeIDs_x=filtered_nodeIDs.loc[filtered_nodeIDs['node_id']<=point_data.shape[1]/3]
	filtered_nodeIDs_y=filtered_nodeIDs.loc[(filtered_nodeIDs['node_id']>point_data.shape[1]/3) & (filtered_nodeIDs['node_id']<=point_data.shape[1]*2/3)]
	filtered_nodeIDs_z=filtered_nodeIDs.loc[(filtered_nodeIDs['node_id']>point_data.shape[1]*2/3) & (filtered_nodeIDs['node_id']<=point_data.shape[1])]
	
	return filtered_nodeIDs_x, filtered_nodeIDs_y, filtered_nodeIDs_z

if __name__ == '__main__':

	print('Parsing from Assembly Config File....')

	data_type=config.assembly_system['data_type']
	application=config.assembly_system['application']
	part_type=config.assembly_system['part_type']
	part_name=config.assembly_system['part_name']
	data_format=config.assembly_system['data_format']
	assembly_type=config.assembly_system['assembly_type']
	assembly_kccs=config.assembly_system['assembly_kccs']   
	assembly_kpis=config.assembly_system['assembly_kpis']
	voxel_dim=config.assembly_system['voxel_dim']
	point_dim=config.assembly_system['point_dim']
	voxel_channels=config.assembly_system['voxel_channels']
	noise_type=config.assembly_system['noise_type']
	mapping_index=config.assembly_system['mapping_index']
	file_names_x=config.assembly_system['data_files_x']
	file_names_y=config.assembly_system['data_files_y']
	file_names_z=config.assembly_system['data_files_z']
	system_noise=config.assembly_system['system_noise']
	aritifical_noise=config.assembly_system['aritifical_noise']
	data_folder=config.assembly_system['data_folder']
	kcc_folder=config.assembly_system['kcc_folder']
	kcc_files=config.assembly_system['kcc_files']

	print('Parsing from Training Config File')

	tree_based_model=cftrain.kmc_params['tree_based_model']
	importance_creteria=cftrain.kmc_params['importance_creteria']
	save_model=cftrain.kmc_params['save_model']
	split_ratio=cftrain.kmc_params['split_ratio']
	plot_kmc=cftrain.kmc_params['plot_kmc']
   
	print('Creating file Structure....')
	
	folder_name=part_type
	train_path='../trained_models/'+part_type
	pathlib.Path(train_path).mkdir(parents=True, exist_ok=True)

	kmc_path=train_path+'/kmc'
	pathlib.Path(kmc_path).mkdir(parents=True, exist_ok=True)

	kmc_plot_path=kmc_path+'/plots'
	pathlib.Path(kmc_plot_path).mkdir(parents=True, exist_ok=True)

	print('Initializing the Assembly System and Measurement System....')
	
	measurement_system=HexagonWlsScanner(data_type,application,system_noise,part_type,data_format)
	vrm_system=VRMSimulationModel(assembly_type,assembly_kccs,assembly_kpis,part_name,part_type,voxel_dim,voxel_channels,point_dim,aritifical_noise)
	get_data=GetTrainData()
	
	print('Importing and preprocessing Cloud-of-Point Data')
	
	dataset=[]
	dataset.append((get_data.data_import(file_names_x,data_folder)).iloc[:,0:point_dim])
	dataset.append((get_data.data_import(file_names_y,data_folder)).iloc[:,0:point_dim])
	dataset.append((get_data.data_import(file_names_z,data_folder)).iloc[:,0:point_dim])
	kcc_dataset=get_data.data_import(kcc_files,kcc_folder)
	point_index=get_data.load_mapping_index(mapping_index)
	
	point_data=pd.concat([dataset[0],dataset[1],dataset[2]],axis=1,ignore_index=True)

	kcc_id=[]
	kmc_list_x=[]
	kmc_list_y=[]
	kmc_list_z=[]

	cop_file_name=vc.voxel_parameters['nominal_cop_filename']

	file_path='../resources/nominal_cop_files/'+cop_file_name
	#Read cop from csv file
	print('Importing Nominal COP')
	nominal_cop=vrm_system.get_nominal_cop(file_path)
	copviz=CopViz(nominal_cop)

	print('Generating KMC for all KCCs...')

	for i in range(assembly_kccs):
		kcc_name="KCC_"+str(i+1)
		kcc_id.append(kcc_name)
		selected_kcc=kcc_dataset.iloc[:,i:i+1]
		filtered_nodeIDs_x,filtered_nodeIDs_y,filtered_nodeIDs_z=kmc_model_build(tree_based_model,point_data,selected_kcc,kcc_name,split_ratio,save_model)
		print(point_dim)
		filtered_nodeIDs_y['node_id']=filtered_nodeIDs_y['node_id']-point_dim
		filtered_nodeIDs_z['node_id']=filtered_nodeIDs_z['node_id']-(2*point_dim)
		
		filtered_nodeIDs_x['node_id']=filtered_nodeIDs_x['node_id'].astype('int')
		filtered_nodeIDs_y['node_id']=filtered_nodeIDs_y['node_id'].astype('int')
		filtered_nodeIDs_z['node_id']=filtered_nodeIDs_z['node_id'].astype('int')

		filename_x=kmc_path+'/'+kcc_name+'_x.csv'
		filename_y=kmc_path+'/'+kcc_name+'_y.csv'
		filename_z=kmc_path+'/'+kcc_name+'_z.csv'

		print('Saving KMCs to disk...')
		filtered_nodeIDs_x.to_csv(filename_x,index = False)
		filtered_nodeIDs_y.to_csv(filename_y,index = False)
		filtered_nodeIDs_z.to_csv(filename_z,index = False)

		stack=copviz.get_data_stacks(filtered_nodeIDs_x,filtered_nodeIDs_y,filtered_nodeIDs_z)

		copviz.plot_multiple_stacks(stack,kmc_plot_path+'/'+kcc_name)




