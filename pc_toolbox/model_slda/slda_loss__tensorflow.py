"""
slda_loss__tensorflow.py

Provides functions for computing loss and gradient for PC training,

Uses Tensorflow implementation under the hood.
"""

import tensorflow as tf

import numpy as np
from scipy.special import gammaln

from pc_toolbox.utils_data import make_slice_for_step

import slda_utils__dataset_manager

from slda_utils__diffable_param_manager__tensorflow import (
    unflatten_to_common_param_dict__tf,
    _unflatten_to_common_param_dict__tf_graph,
    )
from est_local_params__single_doc_map import (
    _calc_nef_map_pi_d_K__tensorflow_graph,
    make_convex_alpha_minus_1,
    DefaultDocTopicOptKwargs,
    )


def make_loss_func_and_grad_func_wrt_paramvec_and_step(
        dataset=None,
        n_batches=1,
        data_seed=42,
        dim_P=None,
        model_hyper_P=None,
        pi_max_iters_first_train_lap=None,
        max_train_laps=None,
        **unused_kwargs):
    ''' Create and return two callable functions: one for loss, one for gradient

    Returns
    -------
    loss_func : func of two args (param_vec, step_id)
        Input:
            param_vec : numpy array, 1D
            step_id : int or None
        Output:
            float
    grad_func : func of two args (param_vec, step_id)
        Input:
            param_vec : numpy array, 1D
            step_id : int or None
        Output:
            grad_vec : numpy array, 1D
    '''
    K = int(dim_P['n_states'])
    V = int(dim_P['n_vocabs'])
    C = int(dim_P['n_labels'])
    S = K * (V - 1) + C * K  # total num params in param vec
    _param_vec = tf.Variable(
        tf.zeros([S], dtype=tf.float64))
    _n_docs = tf.placeholder(shape=[], dtype=tf.int32)
    _word_id_U = tf.placeholder(shape=[None], dtype=tf.int32)
    _word_ct_U = tf.placeholder(shape=[None], dtype=tf.float64)
    _doc_indptr_Dp1 = tf.placeholder(shape=[None], dtype=tf.int32)
    _y_DC = tf.placeholder(shape=[None, C], dtype=tf.float64)
    _y_rowmask = tf.placeholder(shape=[None], dtype=tf.int32)
    _frac_train_laps_completed = tf.placeholder(shape=(), dtype=tf.float64)
    (_loss_x, _loss_y, _loss_pi, _loss_t, _loss_w,
        _pi_DK, _y_proba_DC) = calc_loss__slda__tensorflow_graph(
        param_vec=_param_vec,
        dataset=dict(
            n_docs=_n_docs,
            n_labels=C,
            word_id_U=_word_id_U,
            word_ct_U=_word_ct_U,
            doc_indptr_Dp1=_doc_indptr_Dp1,
            y_DC=_y_DC,
            y_rowmask=_y_rowmask,
            ),
        pi_max_iters_first_train_lap=pi_max_iters_first_train_lap,
        frac_train_laps_completed=_frac_train_laps_completed,
        dim_P=dim_P,
        convex_alpha_minus_1=make_convex_alpha_minus_1(alpha=model_hyper_P['alpha']),
        tau=model_hyper_P['tau'],
        lambda_w=model_hyper_P['lambda_w'],
        weight_x=model_hyper_P['weight_x'],
        weight_y=model_hyper_P['weight_y'],
        )
    _loss_ttl = _loss_x + _loss_y + _loss_pi + _loss_t + _loss_w
    _grad_vec = tf.gradients(_loss_ttl, [_param_vec])[0]
    sess = tf.Session()

    ## BEGIN LOSS FUNC DEFN
    def loss_func(
            param_vec=None,
            step_id=None,
            **unused_kwargs):
        """ Compute loss at provided flat parameter vec

        Returns
        -------
        loss_val : float
        """
        if step_id is None or step_id < 0:
            cur_dataset = dataset
            frac_train_laps_completed = 1.0
        else:
            cur_slice = make_slice_for_step(
                step_id=step_id,
                seed=data_seed,
                n_total=dataset['n_docs'],
                n_batches=n_batches)
            cur_dataset = slda_utils__dataset_manager.slice_dataset(
                dataset=dataset,
                cur_slice=cur_slice)
            frac_train_laps_completed = np.minimum(
                1.0,
                float(step_id) / float(max_train_laps * n_batches))
        loss_ttl = sess.run([_loss_ttl],
            feed_dict={
                _param_vec:param_vec,
                _n_docs:int(cur_dataset['n_docs']),
                _word_id_U:np.asarray(cur_dataset['word_id_U'], dtype=np.int32),
                _word_ct_U:np.asarray(cur_dataset['word_ct_U'], dtype=np.float64),
                _doc_indptr_Dp1:np.asarray(cur_dataset['doc_indptr_Dp1'], dtype=np.int32),
                _y_DC:np.asarray(cur_dataset['y_DC'], dtype=np.float64),
                _y_rowmask:cur_dataset.get(
                    'y_rowmask',
                    np.ones(cur_dataset['n_docs'], dtype=np.int32)),
                _frac_train_laps_completed:frac_train_laps_completed,
                })[0]
        return loss_ttl
    ## END LOSS FUNC DEFN

    ## BEGIN GRAD FUNC DEFN
    def grad_func(
            param_vec=None,
            step_id=None,
            **unused_kwargs):
        """ Compute loss at provided flat parameter vec

        Returns
        -------
        loss_val : float
        """
        if step_id is None or step_id < 0:
            cur_dataset = dataset
            frac_train_laps_completed = 1.0
        else:
            cur_slice = make_slice_for_step(
                step_id=step_id,
                seed=data_seed,
                n_total=dataset['n_docs'],
                n_batches=n_batches)
            cur_dataset = slda_utils__dataset_manager.slice_dataset(
                dataset=dataset,
                cur_slice=cur_slice)
            frac_train_laps_completed = np.minimum(
                1.0,
                float(step_id) / float(max_train_laps * n_batches))
        grad_vec = sess.run([_grad_vec],
            feed_dict={
                _param_vec:param_vec,
                _n_docs:int(cur_dataset['n_docs']),
                _word_id_U:np.asarray(cur_dataset['word_id_U'], dtype=np.int32),
                _word_ct_U:np.asarray(cur_dataset['word_ct_U'], dtype=np.float64),
                _doc_indptr_Dp1:np.asarray(cur_dataset['doc_indptr_Dp1'], dtype=np.int32),
                _y_DC:np.asarray(cur_dataset['y_DC'], dtype=np.float64),
                _y_rowmask:cur_dataset.get(
                    'y_rowmask',
                    np.ones(cur_dataset['n_docs'], dtype=np.int32)),
                _frac_train_laps_completed:frac_train_laps_completed,
                })[0] 
        return grad_vec
    ## END GRAD FUNC DEFN
    return loss_func, grad_func

def calc_loss__slda__tensorflow_graph(
        param_vec=None,
        dim_P=None,
        dataset=None,
        convex_alpha_minus_1=None,
        tau=1.1,
        delta=0.1,
        lambda_w=0.001,
        weight_x=1.0,
        weight_y=1.0,
        weight_pi=1.0,
        return_dict=False,
        rescale_total_loss_by_n_tokens=True,
        frac_train_laps_completed=1.0,
        pi_max_iters_first_train_lap=DefaultDocTopicOptKwargs['pi_max_iters'],
        pi_max_iters=DefaultDocTopicOptKwargs['pi_max_iters'],
        active_proba_thr=0.005,
        **unused_kwargs):
    ''' Compute log probability of bow dataset under topic model.

    Returns
    -------
    log_proba : avg. log probability of dataset under provided LDA model.
        Scaled by number of docs in the dataset.
    '''
    # Unpack dataset
    doc_indptr_Dp1 = dataset['doc_indptr_Dp1']
    word_id_U = dataset['word_id_U']
    word_ct_U = dataset['word_ct_U']
    n_docs = dataset['n_docs']
    y_DC = dataset['y_DC']
    y_rowmask = dataset['y_rowmask']
    
    ## Unpack params
    assert param_vec is not None
    param_dict = _unflatten_to_common_param_dict__tf_graph(param_vec, **dim_P)
    topics_KV = param_dict['topics_KV']
    w_CK = param_dict['w_CK']
    K, _ = topics_KV.get_shape().as_list()
    C, _ = w_CK.get_shape().as_list()

    ## Establish kwargs for pi optimization step
    # Use 'ramp up' strategy to gradually increase per-doc iteration costs.
    # At first, perform only pi_max_iters_first_train_lap.
    # Linearly increase until reaching pi_max_iters,
    # which is designed to happen 50% of way through training.
    #
    # frac_progress : float within (0.0, 1.0)
    #     0.0 when frac_lap == 0
    #     0.5 when frac_lap == 0.25
    #     1.0 when frac_lap >= 0.5
    # cur_pi_max_iters : int
    #     Number of pi iters to run now
    assert pi_max_iters_first_train_lap <= pi_max_iters
    frac_progress = tf.minimum(
        tf.cast(1.0, tf.float64),
        2.0 * frac_train_laps_completed)
    cur_pi_max_iters = tf.cast(
        pi_max_iters_first_train_lap
        + tf.ceil(frac_progress * (pi_max_iters - pi_max_iters_first_train_lap)),
        tf.int32)
    # Pack up into the kwargs handed to pi optimization
    pi_opt_kwargs = dict(**DefaultDocTopicOptKwargs)
    pi_opt_kwargs['pi_max_iters'] = cur_pi_max_iters

    def has_docs_left(
            d, avg_log_proba_x, avg_log_proba_y,
            avg_log_proba_pi, pi_arr, y_arr):
        return d < n_docs
    def update_doc(
            d, avg_log_proba_x, avg_log_proba_y,
            avg_log_proba_pi, pi_arr, y_arr):
        start_d = doc_indptr_Dp1[d]
        stop_d = doc_indptr_Dp1[d+1]
        word_id_d_Ud = word_id_U[start_d:stop_d]
        word_ct_d_Ud = word_ct_U[start_d:stop_d]
        pi_d_K, topics_KUd, _, _ = \
            _calc_nef_map_pi_d_K__tensorflow_graph(
                _word_id_d_Ud=word_id_d_Ud,
                _word_ct_d_Ud=word_ct_d_Ud,
                _topics_KV=topics_KV,
                convex_alpha_minus_1=convex_alpha_minus_1,
                **pi_opt_kwargs)
        pi_arr = pi_arr.write(d, pi_d_K)
        avg_log_proba_pi_d = weight_pi * tf.reduce_sum(
            convex_alpha_minus_1 * tf.log(1e-9 + pi_d_K))
        avg_log_proba_x_d = tf.reduce_sum(
            word_ct_d_Ud * 
            tf.log(tf.matmul(tf.reshape(pi_d_K, (1,K)), topics_KUd)))
        avg_log_proba_x_d += (
            tf.lgamma(1.0 + tf.reduce_sum(word_ct_d_Ud))
            - tf.reduce_sum(tf.lgamma(1.0 + word_ct_d_Ud)))

        log_proba_y_d_C = tf.reduce_sum(
            w_CK * tf.reshape(pi_d_K, (1,K)), axis=1)
        avg_log_proba_y_d = tf.cond(
            y_rowmask[d] > 0,
            lambda: -1.0 * tf.reduce_sum(
                tf.nn.sigmoid_cross_entropy_with_logits(logits=log_proba_y_d_C, labels=y_DC[d])),
            lambda: tf.constant(0.0, dtype=tf.float64))
        y_arr = y_arr.write(d, tf.sigmoid(log_proba_y_d_C))
        return (
            d+1,
            avg_log_proba_x + weight_x * avg_log_proba_x_d,
            avg_log_proba_y + weight_y * avg_log_proba_y_d,
            avg_log_proba_pi + avg_log_proba_pi_d,
            pi_arr,
            y_arr)

    _avg_log_proba_x = tf.constant(0.0, dtype=tf.float64)
    _avg_log_proba_y = tf.constant(0.0, dtype=tf.float64)
    _avg_log_proba_pi = tf.constant(0.0, dtype=tf.float64)
    _K = tf.cast(K, tf.float64)
    _convex_alpha_minus_1 = tf.cast(convex_alpha_minus_1, tf.float64)
    _d = 0
    _pi_arr = tf.TensorArray(dtype=tf.float64, size=n_docs) 
    _y_arr = tf.TensorArray(dtype=tf.float64, size=n_docs) 
    (_d, _avg_log_proba_x, _avg_log_proba_y, _avg_log_proba_pi,
        _pi_arr, _y_arr) = tf.while_loop(
            has_docs_left,
            update_doc,
            loop_vars=[
                _d, _avg_log_proba_x, _avg_log_proba_y, 
                _avg_log_proba_pi, _pi_arr, _y_arr])
    _pi_DK = tf.reshape(_pi_arr.concat(), (n_docs, K))
    _y_proba_DC = tf.reshape(_y_arr.concat(), (n_docs, C))

    _avg_log_proba_topics = (tau - 1.0) * tf.reduce_sum(tf.log(topics_KV))
    _avg_log_proba_w = -1.0 * (
        weight_y * lambda_w * tf.reduce_sum(tf.square(w_CK)))

    scale_ttl = tf.reduce_sum(word_ct_U)
    _avg_log_proba_x /= scale_ttl
    _avg_log_proba_pi /= scale_ttl
    _avg_log_proba_y /= scale_ttl
    _avg_log_proba_topics /= scale_ttl
    _avg_log_proba_w /= scale_ttl

    return (
        -1.0 * _avg_log_proba_x,
        -1.0 * _avg_log_proba_y,
        -1.0 * _avg_log_proba_pi,
        -1.0 * _avg_log_proba_topics,
        -1.0 * _avg_log_proba_w,
        _pi_DK,
        _y_proba_DC)



if __name__ == '__main__':
    import os
    from sklearn.externals import joblib
    from slda_utils__param_manager import (
        flatten_to_differentiable_param_vec,
        unflatten_to_common_param_dict,
        )
    import slda_loss__autograd
    # Simplest possible test
    # Load the toy bars dataset
    # Load "true" bars topics
    # Compute the loss
    dataset_path = os.path.expandvars("$PC_REPO_DIR/datasets/toy_bars_3x3/")
    dataset = slda_utils__dataset_manager.load_dataset(dataset_path, split_name='train')
    n_batches = 100

    # Load "true" 4 bars
    dim_P = dict(n_states=4, n_labels=1, n_vocabs=9)
    model_hyper_P = dict(alpha=1.1, tau=1.1, lambda_w=0.001, weight_x=1.0, weight_y=1.0)
    GP = joblib.load(
        os.path.join(dataset_path, "good_loss_x_K4_param_dict.dump"))
    for key in GP.keys():
        if key not in ['topics_KV', 'w_CK']:
            del GP[key]
    param_vec = flatten_to_differentiable_param_vec(**GP)

    GPA = unflatten_to_common_param_dict(param_vec, **dim_P)
    GPB = unflatten_to_common_param_dict__tf(param_vec, **dim_P)

    print("Checking flat-then-unflat for autograd:")
    for key in GP:
        assert np.allclose(GPA[key], GP[key])
        print("%s OK" % key)
    print("Checking flat-then-unflat for tensorflow:")
    for key in GP:
        assert np.allclose(GPB[key], GP[key])
        print("%s OK" % key)

    calc_loss__tf, calc_grad__tf = make_loss_func_and_grad_func_wrt_paramvec_and_step(
        dataset=dataset,
        n_batches=n_batches,
        dim_P=dim_P,
        model_hyper_P=model_hyper_P,
        max_train_laps=1.0)

    calc_loss__ag, calc_grad__ag = slda_loss__autograd.make_loss_func_and_grad_func_wrt_paramvec_and_step(
        dataset=dataset,
        n_batches=n_batches,
        dim_P=dim_P,
        model_hyper_P=model_hyper_P,
        max_train_laps=1.0)
 
    for method_name, calc_loss_func in [
            ('tensorflow', calc_loss__tf),
            ('autograd', calc_loss__ag)]:
        loss_val = calc_loss_func(param_vec, 0)
        print("loss %.6e via %-20s" % (loss_val, method_name))

    for method_name, calc_grad_func in [
            ('tensorflow', calc_grad__tf),
            ('autograd', calc_grad__ag)]:
        grad_vec = calc_grad_func(param_vec, 0)
        print("l2_norm(grad_vec) %.6e via %-20s" % (np.sqrt(np.sum(np.square(grad_vec))), method_name))




