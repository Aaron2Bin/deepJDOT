# -*- coding: utf-8 -*-
"""
Created on Thu Feb  1 17:21:05 2018

@author: damodara
"""

import numpy as np

import matplotlib.pylab as plt
import dnn
import ot
import os
import json
import copy
import h5py
import importlib
import imutils
from scipy.spatial.distance import cdist 
import matplotlib as mpl
#mpl.use('Agg')
#plt.switch_backend('agg')
#from sklearn import datasets

from matplotlib.colors import ListedColormap

#%% SVHN - MNIST
from da_dataload import svhnn_to_mnist
(source_traindata, source_trainlabel, source_testdata, source_testlabel),\
(target_traindata, target_trainlabel,target_testdata, target_testlabel)=svhnn_to_mnist('min_max', lowerbound_zero=True)
data_name = 'svhnn_mnist'

#%%
plt.imshow(source_traindata[0])
plt.show()
print("Source label:", source_trainlabel[0])
plt.imshow(target_traindata[0])
plt.show()
print("Target label:", target_trainlabel[0])
#%%
def generate_rotated_image(image, lower_angle=-90, upper_angle=90):
    """Generate a rotated image with a random rotation angle"""
    percent = np.random.random()
    percent_to_angle = lambda x: x * (upper_angle-lower_angle) + lower_angle
    #percent_to_scale = lambda x: x * 0.5 + 0.5
    angle = percent_to_angle(percent)
    rotated = imutils.rotate(image, angle, scale=1)
    return rotated, percent

img, angle_per = generate_rotated_image(source_traindata[0])
plt.imshow(img)
print("Angle percentage:", angle_per)
plt.show()
#%%
def generate_rotated_images(images):
    new_images = np.empty_like(images)
    labels = np.empty(images.shape[0])
    for i in range(images.shape[0]):
#        if i % 2500 == 0:
#            print("Generating image", i)
        img, angle = generate_rotated_image(images[i])
        new_images[i] = img
        labels[i] = angle
    return new_images, labels[..., np.newaxis]

print("Generating source_traindata_reg...")
source_traindata_reg, source_trainlabel_reg = generate_rotated_images(target_traindata)
print("Generating source_testdata_reg...")
source_testdata_reg, source_testlabel_reg = generate_rotated_images(target_testdata)
print("Generating target_traindata_reg...")
target_traindata_reg, target_trainlabel_reg = generate_rotated_images(source_traindata)
print("Generating target_testdata_reg...")
target_testdata_reg, target_testlabel_reg = generate_rotated_images(source_testdata)
        
#%%
#from keras.utils.np_utils import to_categorical
#source_trainlabel_cat = to_categorical(source_trainlabel)
#source_testlabel_cat = to_categorical(source_testlabel)
##test_label_cat = to_categorical(y_test)
##
#target_trainlabel_cat = to_categorical(target_trainlabel)
#target_testlabel_cat = to_categorical(target_testlabel)
##target_label_cat = to_categorical(target_label)
#%%
#n_class = len(np.unique(source_trainlabel))
n_dim = np.shape(source_traindata)
n_outputs = source_trainlabel_reg.shape[-1] # number of output units in output layer
del source_traindata, source_testdata, target_traindata, target_testdata
del source_trainlabel, source_testlabel, target_trainlabel, target_testlabel
#%%
pathname ='results2/'
filesave = True
 #%%
def make_trainable(net, val):
    net.trainable = val
    for l in net.layers:
        l.trainable = val 
#%%
def feature_extraction(model, data, out_layer_num=-2, out_layer_name=None):
    '''
    extract the features from the pre-trained model
    inp_layer_num - input layer
    out_layer_num -- from which layer to extract the features
    out_layer_name -- name of the layer to extract the features
    '''
    if out_layer_name is None:
        intermediate_layer_model = dnn.Model(inputs=model.layers[0].input,
                             outputs=model.layers[out_layer_num].output)
        intermediate_output = intermediate_layer_model.predict(data)
    else:
        intermediate_layer_model = dnn.Model(inputs=model.layers[0].input,
                             outputs=model.get_layer(out_layer_name).output)
        intermediate_output = intermediate_layer_model.predict(data)
        
    
    return intermediate_output
    
#%%
#def tsne_plot(xs, xt, xs_label, xt_label, subset=True, title=None, pname=None):
#    num_test=1000
#    import matplotlib.cm as cm
#    if subset:
#        combined_imgs = np.vstack([xs[0:num_test, :], xt[0:num_test, :]])
#        combined_labels = np.vstack([xs_label[0:num_test, :],xt_label[0:num_test, :]])
#        combined_labels = combined_labels.astype('int')
#        combined_domain = np.vstack([np.zeros((num_test,1)),np.ones((num_test,1))])
#    
#    from sklearn.manifold import TSNE
#    tsne = TSNE(perplexity=30, n_components=2, init='pca', n_iter=3000)
#    source_only_tsne = tsne.fit_transform(combined_imgs)
#    plt.figure(figsize=(15,15))
#    plt.scatter(source_only_tsne[:num_test,0], source_only_tsne[:num_test,1], c=combined_labels[:num_test].argmax(1),
#                s=50, alpha=0.5,marker='o', cmap=cm.jet, label='source')
#    plt.scatter(source_only_tsne[num_test:,0], source_only_tsne[num_test:,1], c=combined_labels[num_test:].argmax(1),
#                s=50, alpha=0.5,marker='+',cmap=cm.jet,label='target')
#    plt.axis('off')
#    plt.legend(loc='best')
#    plt.title(title)
#    if filesave:
#        plt.savefig(os.path.join(pname,title+'.png'),bbox_inches='tight', pad_inches = 0,
#                    format='png')
#    else:
#        plt.savefig(title+'.png')
#    plt.close() 


#%% source model
from architectures import assda_feat_ext#, classifier, res_net50_fe 
from architectures import regressor
ms = dnn.Input(shape=(n_dim[1],n_dim[2],n_dim[3]))
fes = assda_feat_ext(ms, small_model=True)
nets = regressor(fes, n_outputs)
source_model = dnn.Model(ms, nets)
#%%
optim = dnn.keras.optimizers.Adam(lr=0.0002)#,beta_1=0.999, beta_2=0.999)
source_model.compile(optimizer=optim, loss='binary_crossentropy', metrics=['mae'])
checkpoint = dnn.keras.callbacks.ModelCheckpoint('bst.hdf5', monitor = 'val_loss', verbose = 0, save_best_only = True, mode = 'auto')
early_stop = dnn.keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=1e-5, 
                                                       patience=5, verbose=0, mode='auto')
callbacks_list = [early_stop, checkpoint]
#%%
source_model.fit(source_traindata_reg, source_trainlabel_reg, batch_size=128, epochs=10,
                  validation_split=0.16, callbacks=callbacks_list)

# pp='/home/damodara/OT/DA/ALJDOT/codes/results/adaa_source/mnist_usps'
# source_model = dnn.keras.models.load_model(os.path.join(pp, 'mnist_usps_sourcemodel.h5'))

# source_model.load_weights('bst.hdf5')
smodel_train_mae = source_model.evaluate(source_traindata_reg, source_trainlabel_reg)[1]
smodel_test_mae = source_model.evaluate(source_testdata_reg, source_testlabel_reg)[1]
smodel_target_trainmae = source_model.evaluate(target_traindata_reg, target_trainlabel_reg)[1]
smodel_target_testmae = source_model.evaluate(target_testdata_reg, target_testlabel_reg)[1]
print("source train mae using source model", smodel_train_mae)
print("target train mae using source model", smodel_target_trainmae)
print("source test mae using source model", smodel_test_mae)
print("target test mae using source model", smodel_target_testmae)


#%%
if filesave:
    source_model.save(os.path.join(pathname,data_name+'_Sourcemodel.h5'))
# source_model = dnn.keras.models.load_model(os.path.join(pathname, 'mnist_usps_Sourcemodel.h5'))

#%%
#sd = feature_extraction(source_model, source_testdata[:5000,:], out_layer_num=-2)
#td = feature_extraction(source_model, target_testdata[:5000,:], out_layer_num=-2)
## td = feature_extraction(source_model, target_testdata, out_layer_num=-2)
#title = data_name+'_smodel'
#tsne_plot(sd, td, source_testlabel_cat, target_testlabel_cat, title=title, pname=pathname)
#%% 

main_input = dnn.Input(shape=(n_dim[1],n_dim[2],n_dim[3]))
fe = assda_feat_ext(main_input, l2_weight=0.0, small_model=True)
fe_size=fe.get_shape().as_list()[1]
fe_model = dnn.Model(main_input, fe, name= 'fe_model')
#
rg_input = dnn.Input(shape=(fe.get_shape().as_list()[1],))
net = regressor(rg_input , n_outputs,l2_weight=0.0)
rg_model = dnn.Model(rg_input, net, name ='regressor')
#fe_size = 768
#%% aljdot model
main_input = dnn.Input(shape=(n_dim[1],n_dim[2],n_dim[3]))
ffe = fe_model(main_input)
net = rg_model(ffe)
#con_cat = dnn.concatenate([net, ffe ], axis=1)
model = dnn.Model(inputs=main_input, outputs=[net, ffe])
#model.set_weights(source_model.get_weights())

#%% Target model loss and fit function
optim = dnn.keras.optimizers.Adam(lr=0.0001)#,beta_1=0.999, beta_2=0.999)
sample_size=50

class jdot_align(object):
    def __init__(self, model, batch_size, n_outputs, optim, allign_loss=1.0, tar_cl_loss=1.0, 
                 sloss=0.0,tloss=1.0,int_lr=0.01, ot_method='emd',
                 jdot_alpha=0.01, lr_decay=True, verbose=1):
        self.model = model
        self.batch_size = batch_size
        self.sbatch_size = batch_size
        self.n_outputs= n_outputs
        self.optimizer= optim
        self.gamma=dnn.K.zeros(shape=(self.batch_size, self.batch_size))
        self.tgamma = dnn.K.zeros(shape=(self.batch_size, self.batch_size))
        self.train_cl =dnn.K.variable(tar_cl_loss)
        self.train_algn=dnn.K.variable(allign_loss)
        self.sloss = dnn.K.variable(sloss)
        self.tloss = dnn.K.variable(tloss)
        self.verbose = verbose
        self.int_lr =int_lr
        self.lr_decay= lr_decay
        #
        self.ot_method = ot_method
        self.jdot_alpha=jdot_alpha
        # target regression L2 loss       
        def regressor_loss(y_true, y_pred):
            '''
            sourceloss + target regression loss
            regression loss based on binary cross entropy in the target domain
            1:batch_size - is source samples
            batch_size:end - is target samples
            self.gamma - is the optimal transport plan
            '''
            # source true labels
            ys = y_true[:self.batch_size,:]
            # target prediction
            ypred_t = y_pred[self.batch_size:2*self.batch_size,:]
            source_ypred = y_pred[:self.batch_size,:]
            source_loss = dnn.K.mean(dnn.K.binary_crossentropy(ys, source_ypred))
            # categorical cross entropy loss
            ypred_t = dnn.K.log(ypred_t)
            # loss calculation based on double sum (sum_ij (ys^i, ypred_t^j))
            loss = -dnn.K.dot(ys, dnn.K.transpose(ypred_t))
            return self.train_cl*(self.tloss*dnn.K.sum(self.gamma * loss) + self.sloss*source_loss)

        self.regressor_loss = regressor_loss
        
        def source_regressor_loss(y_true, y_pred):
            '''
            regressor loss based on binary cross entropy in the source domain
            1:batch_size - is source samples
            batch_size:end - is target samples
            '''
            # source true labels
            ys = y_true[:self.batch_size,:]
            source_ypred = y_pred[:self.batch_size,:]
            source_loss = dnn.K.mean(dnn.K.binary_crossentropy(ys, source_ypred))
             
            return self.sloss*source_loss
        self.source_regressor_loss = source_regressor_loss
        
        def L2_dist(x,y):
            '''
            compute the squared L2 distance between two matrics
            '''
            dist = dnn.K.reshape(dnn.K.sum(dnn.K.square(x),1), (-1,1))
            dist += dnn.K.reshape(dnn.K.sum(dnn.K.square(y),1), (1,-1))
            dist -= 2.0*dnn.K.dot(x, dnn.K.transpose(y))  
            return dist
 
        def align_loss(y_true, y_pred):
            '''
            source and target alignment loss in the intermediate layers of the target model
            alignment is performed in the target model (both source and target features are from target model)
            y-true - is dummy value( that is full of zeros)
            y-pred - is the value of intermediate layers in the target model
            1:batch_size - is source samples
            batch_size:end - is target samples            
            '''
            # source domain features            
            gs = y_pred[:self.batch_size,:]
            # target domain features
            gt = y_pred[self.batch_size:2*self.batch_size,:]
            gdist = L2_dist(gs,gt)  
            loss = self.jdot_alpha*dnn.K.sum(self.gamma*gdist)
            return self.train_algn*loss
        self.align_loss= align_loss
 

 
    def fit(self, source_traindata, ys_label, target_traindata, target_testdata=None,
            target_testlabel=None, n_iter=5000):
        '''
        ys_label - source data true labels
        '''
        ns = source_traindata.shape[0]
        nt= target_traindata.shape[0]
        method=self.ot_method # for optimal transport
        alpha=self.jdot_alpha
        t_mae = []
        t_loss =[]
        tloss = dnn.K.eval(self.tloss)
        g_metric ='deep'
#        def mini_batch_class_balanced(label, sample_size=20, shuffle=False):
#            ''' sample the mini-batch with class balanced
#            '''
#            label = np.argmax(label, axis=1)
#            if shuffle:
#                rindex = np.random.permutation(len(label))
#                label = label[rindex]
#
#            n_class = len(np.unique(label))
#            index = []
#            for i in range(n_class):
#                s_index = np.nonzero(label == i)
#                s_ind = np.random.permutation(s_index[0])
#                index = np.append(index, s_ind[0:sample_size])
#                #          print(index)
#            index = np.array(index, dtype=int)
#            return index

        self.model.compile(optimizer= optim, loss =[self.regressor_loss, self.align_loss])
        dnn.K.set_value(self.model.optimizer.lr, self.int_lr)        
        for i in range(n_iter):
            if self.lr_decay and i%10000 ==0:
                # p = float(i) / n_iter
                # lr = self.int_lr / (1. + 10 * p)**0.9
                lr = dnn.K.get_value(self.model.optimizer.lr)
                dnn.K.set_value(self.model.optimizer.lr, lr*0.1)
            # fixing f and g, and computing optimal transport plan (gamma)
#            if cal_bal:
#                s_ind = mini_batch_class_balanced(ys_label, sample_size=sample_size)
#                self.sbatch_size = len(s_ind)
#            else:
            s_ind = np.random.choice(ns, self.batch_size)
            self.sbatch_size = self.batch_size

            t_ind = np.random.choice(nt, self.batch_size)

            
            xs_batch, ys = source_traindata[s_ind], ys_label[s_ind]
            xt_batch = target_traindata[t_ind]


            l_dummy = np.zeros_like(ys)
            g_dummy = np.zeros((2*self.batch_size, fe_size))
            s = xs_batch.shape
            
            # concat of source and target samples and prediction
            modelpred = self.model.predict(np.vstack((xs_batch, xt_batch)))
            # intermediate features
            gs_batch = modelpred[1][:self.batch_size, :]
            gt_batch = modelpred[1][self.batch_size:, :]
            # softmax prediction of target samples
            ft_pred = modelpred[0][self.batch_size:,:]

            if g_metric=='orginal':
                # compution distance metric
                if len(s) == 3:  # when the input is image, convert into 2D matrix
                    C0 = cdist(xs_batch.reshape(-1, s[1] * s[2]), xt_batch.reshape(-1,
                                                                                   s[1] * s[2]), metric='sqeuclidean')

                elif len(s) == 4:
                    C0 = cdist(xs_batch.reshape(-1, s[1] * s[2] * s[3]), xt_batch.reshape(-1,
                                                                                          s[1] * s[2] * s[3]),metric='sqeuclidean')

            else:
                # distance computation between source and target
                C0 = cdist(gs_batch, gt_batch, metric='sqeuclidean')
            
           #  if i==0:
           #      scale = np.max(C0)
           #  C0/=scale
            C1 = cdist(ys, ft_pred, metric='sqeuclidean')
            
            C= alpha*C0+tloss*C1
                             
            # transportation metric
            
            if method == 'emd':
                 gamma=ot.emd(ot.unif(gs_batch.shape[0]),ot.unif(gt_batch.shape[0]),C)
            elif method =='sinkhorn':
                 gamma=ot.sinkhorn(ot.unif(gs_batch.shape[0]),ot.unif(gt_batch.shape[0]),C,reg)
            # update the computed gamma                      
            dnn.K.set_value(self.gamma, gamma)

            
            data = np.vstack((xs_batch, xt_batch))
            hist = self.model.train_on_batch([data], [np.vstack((ys, l_dummy)), g_dummy])
            t_loss.append(hist[0])
            if self.verbose:
                if i%50==0:
                    print ('iter ={:},tl_loss ={:f}, fe_loss ={:f},  tot_loss={:f}'.format(i, hist[1],
                          hist[2], hist[0]))
                    if target_testdata is not None:
                        if target_testlabel is not None:
                            tpred = self.model.predict(target_testdata)[0]
                            mae = np.mean(np.abs(tpred - target_testlabel))
                            t_mae.append(mae)
    #                        t_acc.append(np.mean(np.argmax(target_testlabel,1)==np.argmax(tpred,1)))
                            print('Target MAE:', mae)
                        else:
                            print("No target_testlabel to evaluate")
                    else:
                        print("No target_testdata to evaluate")
                    
        return hist, t_loss, t_mae
            
        

    def predict(self, data):
        ypred = self.model.predict(data)[1]
        return ypred

    def evaluate(self, data, label):
        ypred = self.model.predict(data)[0]
        score = np.mean(np.abs(ypred - label))
#        score = np.mean(np.argmax(label,1)==np.argmax(ypred[0],1))
        return score
    
    
#%%
model.set_weights(source_model.get_weights())
#model.set_weights(allweights)
batch_size=500
sample_size=50
sloss = 1.0; tloss=0.0001; int_lr=0.001; jdot_alpha=0.001
al_model = jdot_align(model, batch_size, n_outputs, optim,allign_loss=1.0,
                      sloss=sloss,tloss=tloss,int_lr=int_lr,jdot_alpha=jdot_alpha,lr_decay=True)
h,t_loss,tmae = al_model.fit(source_traindata_reg, source_trainlabel_reg, target_traindata_reg,
                             target_testdata=target_testdata_reg, target_testlabel=target_testlabel_reg,
                            n_iter=1000)
#%%
tmodel_source_train_mae = al_model.evaluate(source_traindata_reg, source_trainlabel_reg)
print("source train mae using source+target model", tmodel_source_train_mae)
tmodel_tar_train_mae = al_model.evaluate(target_traindata_reg, target_trainlabel_reg)
print("target train mae using source+target model", tmodel_tar_train_mae)
tmodel_source_test_mae = al_model.evaluate(source_testdata_reg, source_testlabel_reg)
print("source test mae using source+target model", tmodel_source_test_mae)
tmodel_tar_test_mae = al_model.evaluate(target_testdata_reg, target_testlabel_reg)
print("target test mae using source+target model", tmodel_tar_test_mae)

#print("target domain acc", tmodel_tar_test_acc)
#print("trained on target, source acc", tmodel_source_test_acc)
#print("maximum target domain acc", np.max(tacc))

allweights = model.get_weights()
#%% deepjdot model save

if filesave:
    al_model.model.save(os.path.join(pathname, data_name+'tmodel_tloss_'+str(tloss)+'_jalpa_'+str(jdot_alpha)+'.h5'))
    al_model.model.save_weights(os.path.join(pathname, data_name+'t_weights_tloss_'+str(tloss)+'_jalpa_'+str(jdot_alpha)+'.h5'))
    sss=al_model.model.to_json()
    # np.savez(os.path.join(pathname, data_name+'_DeepJDOT_parameter.npz'), allign_loss = 1.0, sloss=1.0, t_loss=1.0, int_lr=0.0001,
    #          jdot_alpha=0.001, lr_decay=True)
    #
    # #%% save results in txt file
    fn = os.path.join(pathname, data_name+'_deepjdot_acc.txt')
    fb = open(fn,'w')
    fb.write(" data name = %s DeepJDOT\n" %(data_name))
    fb.write("DeepJDOT param, sloss =%f, tloss=%f,jdot_alpha=%f, int_lr=%f\n" %(sloss, tloss, jdot_alpha, int_lr))
    fb.write("=============================\n")
    fb.write("Trained in source domain, source data train acc =%f\n" %(smodel_train_acc))
    fb.write("Trained in source domain, source data test acc=%f\n" %(smodel_test_acc))
    fb.write("Trained in source domain, target data train acc=%f\n" %(smodel_target_trainacc))
    fb.write("Trained in source domain, target data test acc=%f\n" %(smodel_target_testacc))
    fb.write("=======DeepJDOT Results====================\n")
    fb.write("Trained with DeepJDOT model, source data train acc=%f\n" %(tmodel_source_train_acc))
    fb.write("Trained with DeepJDOT model, source data test acc=%f\n" %(tmodel_source_test_acc))
    fb.write("Trained with DeepJDOT model, target data train acc=%f\n" %(tmodel_tar_train_acc))
    fb.write("Trained with DeepJDOT model, target data test acc=%f\n" %(tmodel_tar_test_acc))
    # fb.write("Target domain DeepJDOT model, target data max acc = %f\n" %(np.max(tacc)))
    fb.close()

#    np.savez(os.path.join(pathname, data_name+'deepjdot_objvalues.npz'), hist_loss = h, total_loss=t_loss, target_acc=tacc)
#%%
al_sourcedata = model.predict(source_traindata[:2000,:])[1]
al_targetdata = model.predict(target_traindata[:2000,:])[1]

#%%

title = data_name+'_DeepJDOT'
tsne_plot(al_sourcedata, al_targetdata, source_trainlabel_cat, target_trainlabel_cat,
          title=title, pname=os.path.join(pathname))
