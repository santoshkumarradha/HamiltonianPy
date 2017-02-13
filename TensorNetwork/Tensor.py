'''
Tensor and tensor operations, including:
1) classes: Label,Tensor
2) functions: contract
'''

from numpy import ndarray,asarray,product,einsum
from collections import namedtuple,Counter,OrderedDict
from copy import copy,deepcopy
from HamiltonianPy import QuantumNumberCollection
from HamiltonianPy.Misc import truncated_svd

__all__=['Label','Tensor','contract']

class Label(tuple):
    '''
    The label of a dimension of a tensor.
    Attributes:
        names: ('identifier','_prime_')
            The names of the immutable part of the label.
        qnc: integer or QuantumNumberCollection
            When integer, it is the dimension of the label;
            When QuantumNumberCollection, it is the quantum number collection of the label.
    '''
    repr_form=1

    def __new__(cls,identifier,prime=False,qnc=None):
        '''
        Parameters:
            identifier: any hashable object
                The index of the label
            prime: logical, optional
                When True, the label is in the prime form;
                otherwise not.
            qnc: integer or QuantumNumberCollection, optional
                When integer, it is the dimension of the label;
                When QuantumNumberCollection, it is the quantum number collection of the label.
        '''
        self=tuple.__new__(cls,(identifier,prime))
        self.names=('identifier','_prime_')
        self.qnc=qnc
        return self

    def __getnewargs__(self):
        '''
        Return the arguments for Label.__new__, required by copy and pickle.
        '''
        return tuple(self)+(self.qnc,)

    def __getstate__(self):
        '''
        Since Label.__new__ constructs everything, self.__dict__ can be omitted for copy and pickle.
        '''
        pass

    def __getattr__(self,key):
        '''
        Overloaded operator(.).
        '''
        try:
            return self[self.names.index(key)]
        except ValueError:
            raise AttributeError()

    def __repr__(self):
        '''
        Convert an instance to string.
        '''
        if self.repr_form==0:
            if self[-1]:
                return "Label%s%s"%((tuple.__repr__(self[0:-1])),"'")
            else:
                return "Label%s"%(tuple.__repr__(self[0:-1]))
        elif self.repr_form==1:
            if self[-1]:
                return "Label%s%s,with qnc=%s"%((tuple.__repr__(self[0:-1])),"'",self.qnc)
            else:
                return "Label%s,with qnc=%s"%(tuple.__repr__(self[0:-1]),self.qnc)
        else:
            if self[-1]:
                return "Label%s%s,with qnc(id=%s)=%s"%((tuple.__repr__(self[0:-1])),"'",id(self.qnc),self.qnc)
            else:
                return "Label%s,with qnc(id=%s)=%s"%(tuple.__repr__(self[0:-1]),id(self.qnc),self.qnc)

    def replace(self,**karg):
        '''
        Return a new label with some of its attributes replaced.
        Parameters:
            karg: dict in the form (key,value), with
                key: string
                    The attributes of the label
                value: any object
                    The corresponding value.
        Returns: Label
            The new label.
        '''
        result=tuple.__new__(self.__class__,map(karg.pop,self.names,self))
        for key,value in self.__dict__.iteritems():
            setattr(result,key,karg.pop(key,value))
        if karg:
            raise ValueError("Label replace error: %s are not the attributes of the label."%karg.keys())
        return result

    @classmethod
    def repr_qnc_on(cls,id=False):
        '''
        Turn on the qnc part in the repr, and optionally, the id of the qnc.
        '''
        if id:
            cls.repr_form=2
        else:
            cls.repr_form=1

    @classmethod
    def repr_qnc_off(cls):
        '''
        Turn off the qnc part in the repr.
        '''
        cls.repr_form=0

    @property
    def prime(self):
        '''
        The prime of the label.
        '''
        temp=list(self)
        temp[-1]=not temp[-1]
        result=tuple.__new__(self.__class__,temp)
        for key,value in self.__dict__.iteritems():
            tuple.__setattr__(result,key,value)
        return result

    @property
    def n(self):
        '''
        The length of the dimension this label labels.
        '''
        if isinstance(self.qnc,QuantumNumberCollection):
            return self.qnc.n
        else:
            return self.qnc

    @property
    def qn_on(self):
        '''
        True for qnc is an instance of QuantumNumberCollection otherwise False.
        '''
        return isinstance(self.qnc,QuantumNumberCollection)

class Tensor(ndarray):
    '''
    Tensor class with labeled axes.
    Attributes:
        labels: list of Label
            The labels of the axes.
    '''

    def __new__(cls,data,labels):
        '''
        Initialize an instance through the explicit construction, i.e. constructor.
        Parameters:
            data: ndarray like
                The data of the Tensor.
            labels: list of Label
                The labels of the Tensor.
        '''
        data=asarray(data)
        assert len(labels)==len(data.shape)
        for label,dim in zip(labels,data.shape):
            assert isinstance(label,Label)
            #if label.n is None:
            #    label.qnc=dim
            #else:
            #    assert label.n==dim
        result=data.view(cls)
        result.labels=labels
        return result

    def __array_finalize__(self,obj):
        '''
        Initialize an instance through both explicit and implicit constructions, i.e. construtor, view and slice.
        '''
        if obj is None:
            return
        else:
            self.labels=getattr(obj,'labels',None)

    def __reduce__(self):
        '''
        numpy.ndarray uses __reduce__ to pickle. Therefore this mehtod needs overriding for subclasses.
        '''
        temp=super(Tensor,self).__reduce__()
        return (temp[0],temp[1],temp[2]+(self.labels,))

    def __setstate__(self,state):
        '''
        Set the state of the Tensor for pickle and copy.
        '''
        self.labels=state[-1]
        super(Tensor,self).__setstate__(state[0:-1])

    def __deepcopy__(self,demo):
        '''
        Deepcopy of the Tensor.
        '''
        return Tensor(data=super(Tensor,self).__deepcopy__(demo),labels=deepcopy(self.labels))

    def __str__(self):
        '''
        Convert an instance to string.
        '''
        if self.ndim>1:
            return "%s(labels=%s,data=\n%s)"%(self.__class__.__name__,self.labels,ndarray.__str__(self))
        else:
            return "%s(labels=%s, data=%s)"%(self.__class__.__name__,self.labels,ndarray.__str__(self))

    def label(self,axis):
        '''
        Return the corresponding label of an axis.
        Parameters:
            axis: integer
                The axis whose corresponding label is inquired.
        Returns: any hashable object
            The corresponding label.
        '''
        return self.labels[axis]

    def axis(self,label):
        '''
        Return the corresponding axis of a label.
        Parameters:
            label: Label
                The label whose corresponding axis is inquired.
        Returns: integer
            The corresponding axis.
        '''
        return self.labels.index(label)

    def relabel(self,news,olds=None):
        '''
        Change the labels of the tensor.
        Parameters:
            news: list of Label
                The new labels of the tensor's axes.
            olds: list of Label, optional
                The old labels of the tensor's axes.
        '''
        if olds is None:
            assert len(news)==self.ndim
            #assert all(new.n==dim for new,dim in zip(news,self.shape))
            self.labels=news
        else:
            assert len(news)==len(olds)
            #assert all(new.n==old.n for new,old in zip(news,olds))
            for old,new in zip(olds,news):
                self.labels[self.axis(old)]=new

    def transpose(self,labels=None,axes=None):
        '''
        Change the order of the tensor's axes and return the new tensor.
        Parameters:
            labels: list of Label, optional
                The permutation of the original labels.
            axes: list of integers, optional
                The permutation of the original axes.
        Returns: Tensor
            The new tensor with the reordered axes.
        NOTE: labels and axes SHOULD NOT be assigned at the same time. BUT if this does happen, axes will be omitted.
        '''
        if labels is not None:
            assert len(labels)==len(self.labels)
            return Tensor(self.view(ndarray).transpose([self.axis(label) for label in labels]),labels=labels)
        elif axes is not None:
            assert len(axes)==len(self.labels)
            return Tensor(self.view(ndarray).transpose(axes),labels=[self.label(axis) for axis in axes])
        else:
            return self.transpose(axes=range(self.ndim-1,-1,-1))

    def take(self,indices,label=None,axis=None):
        '''
        Take elements from a tensor along an axis.
        Parameters:
            indices: integer / list of integers
                The indices of the values to extract.
            label: Label, optional
                The label of the axis along which to take values.
            axis: integer, optional
                The axis along which to take values.
        Returns: Tensor
            The extracted parts of the tensor.
        NOTE: label and axis SHOULD NOT be assigned at the same time. BUT if this does happen, axis will be omitted.
        '''
        if label is not None:
            if isinstance(indices,int) or isinstance(indices,long):
                labels=[deepcopy(lb) for lb in self.labels if lb!=label]
            else:
                labels=deepcopy(self.labels)
            return Tensor(self.view(ndarray).take(indices,axis=self.axis(label)),labels=labels)
        elif axis is not None:
            if isinstance(indices,int) or isinstance(indices,long):
                labels=[deepcopy(label) for i,label in enumerate(self.labels) if i!=axis]
            else:
                labels=deepcopy(self.labels)
            return Tensor(self.view(ndarray).take(indices,axis=axis),labels=labels)
        else:
            raise ValueError("Tensor take error: label and axis cannot be None simultaneously.")

    def merge(self,olds,new):
        '''
        Merge some labels of the tensor into a new one.
        Parameters:
            olds: list of Label
                The old labels to be merged.
            new: Label
                The new label.
        Returns: Tensor
            The new tensor.
        '''
        axes,labels,shape,yet=[],[],(),True
        for axis,label in enumerate(self.labels):
            if label in olds:
                if yet:
                    axes.extend([self.axis(old) for old in olds])
                    labels.append(new)
                    shape+=(-1,)
                    yet=False
            else:
                axes.append(axis)
                labels.append(label)
                shape+=(self.shape[axis])
        result=self.transpose(axes=axes)
        if olds[0].qn_on:
            
        else:
            new.qnc=np.product([old.qnc for old in olds])
            result=Tensor(asarray(result).reshape(shape),labels=labels)

    def split(self,old,news):
        '''
        Split a label into small ones.
        Parameters:
            old: Label
                The label to be split.
            news: list of Label
                The new labels.
        Returns: Tensor
            The new tensor.
        '''
        pass

    def svd(self,labels1,new,labels2,nmax=None,tol=None,return_truncation_err=False,**karg):
        '''
        Perform the svd.
        Parameters:
            labels1,labels2: list of any hashable object
                The axis labels of the two groups.
            new: any hashable object
                The new axis label after the svd.
            nmax,tol,return_truncation_err:
                Please refer to HamiltonianPy.Math.linalg.truncated_svd for details.
        Returns:
            U,S,V: Tensor
                The result tensor.
            err: float64, optional
                The truncation error.
        '''
        def axes_and_shape(labels):
            axes=[self.axis(label) for label in labels]
            shape=tuple(asarray(self.shape)[axes])
            return axes,shape
        axes1,shape1=axes_and_shape(labels1)
        axes2,shape2=axes_and_shape(labels2)
        if set(xrange(self.ndim))-set(axes1+axes2):
            raise ValueError('Tensor svd error: all axis should be divided into two group to perform the svd.')
        m=asarray(self).transpose(axes1+axes2).reshape((product(shape1),)+(product(shape2),))
        temp=truncated_svd(m,full_matrices=False,nmax=nmax,tol=tol,return_truncation_err=return_truncation_err,**karg)
        u,s,v=temp[0],temp[1],temp[2]
        U=Tensor(u.reshape(shape1+(-1,)),labels=labels1+[new])
        S=Tensor(s,labels=[new])
        V=Tensor(v.reshape((-1,)+shape2),labels=[new]+labels2)
        if return_truncation_err:
            err=temp[3]
            return U,S,V,err
        else:
            return U,S,V

def contract(*tensors,**karg):
    '''
    Contract a collection of tensors.
    Parameters:
        tensors: list of Tensor
            The tensors to be contracted.
        karg['sequence']: list of tuple, 'sequential','reversed'
            The contraction sequence of the tensors.
        karg['reserve']: list of hashable objects
            The labels that are repeated but not summed over.
    Returns: Tensor
        The contracted tensor.
    '''
    if len(tensors)==0:
        raise ValueError("Tensor contract error: there are no tensors to contract.")
    sequence=karg.pop('sequence',[])
    if len(sequence)==0:
        return _contract_(*tensors,**karg)
    else:
        if sequence=='sequential':
            sequence=[(i,) for i in xrange(len(tensors))]
        elif sequence=='reversed':
            sequence=[(i,) for i in xrange(len(tensors)-1,-1,-1)]
        for i,seq in enumerate(sequence):
            temp=[tensors[i] for i in seq]
            if i==0:
                result=_contract_(*temp,**karg)
            else:
                result=_contract_(result,*temp,**karg)
        return result

def _contract_(*tensors,**karg):
    '''
    Contract a small collection of tensors.
    '''
    replace,reserve={},{}
    for key in karg.get('reserve',[]):
        replace[key]=key
        reserve[key]=True
    lists=[tensor.labels for tensor in tensors]
    alls=[replace.get(label,label) for labels in lists for label in labels]
    counts=Counter(alls)
    table={key:i for i,key in enumerate(counts)}
    subscripts=[''.join(chr(table[label]+97) for label in labels) for labels in lists]
    contracted_labels=[label for label in alls if (counts[label]==1 or reserve.pop(label,False))]
    contracted_subscript=''.join(chr(table[label]+97) for label in contracted_labels)
    return Tensor(einsum('%s->%s'%(','.join(subscripts),contracted_subscript),*tensors),labels=contracted_labels)