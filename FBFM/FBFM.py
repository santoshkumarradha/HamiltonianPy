'''
======================
Flat band ferromagnets
======================

Spin excitations for flat band ferromagnets, including:
    * constants: FBFM_PRIORITY
    * classes: FBFMBasis, FBFM, EB
    * functions: optrep, FBFMEB, FBFMPOS
'''

__all__=['FBFM_PRIORITY','FBFMBasis','optrep','FBFM','EB','FBFMEB','FBFMPOS']

import numpy as np
import HamiltonianPy as HP
import HamiltonianPy.Misc as HM
import scipy.linalg as sl
import itertools as it
import matplotlib.pyplot as plt
from fmatrix import *
from collections import OrderedDict
from fractions import Fraction

FBFM_PRIORITY=('spin','scope','nambu','site','orbital')

class FBFMBasis(object):
    '''
    The basis of the projected single particle space.

    Attributes
    ----------
    BZ : FBZ
        The first Brillouin zone.
    polarization : 'up'/'dw'
        The polarization of the ground state.
    filling : Fraction
        The filling factor.
    _E1_,_E2_ : 2d ndarray
        The eigenvalues of the single particle space.
    _U1_,_U2_ : 3d ndarray
        The eigenvectors of the single particle space.
    '''

    def __init__(self,BZ=None,polarization='up',filling=Fraction(1,4)):
        '''
        Constructor.

        Parameters
        ----------
        BZ : FBZ, optional
            The first Brillouin zone.
        polarization : 'up'/'dw', optional
            The polarization of the ground state.
        filling : Fraction, optional
            The filling factor.
        '''
        assert polarization in ('up','dw')
        self.BZ=BZ
        self.polarization=polarization
        self.filling=filling

    def set(self,matrix):
        '''
        Set the basis.

        Parameters
        ----------
        matrix : callable
            The function to get the single particle matrix.
        '''
        Eup,Uup,Edw,Udw=[],[],[],[]
        for k in [()] if self.BZ is None else self.BZ.mesh('k'):
            m=matrix(k)
            es,us=sl.eigh(m[:m.shape[0]/2,:m.shape[0]/2])
            Edw.append(es)
            Udw.append(us)
            es,us=sl.eigh(m[m.shape[0]/2:,m.shape[0]/2:])
            Eup.append(es)
            Uup.append(us)
        Eup,Uup=np.asarray(Eup),np.asarray(Uup).transpose((1,0,2))
        Edw,Udw=np.asarray(Edw),np.asarray(Udw).transpose((1,0,2))
        if self.polarization=='up':
            self._E1_=Edw
            self._E2_=Eup
            self._U1_=Udw
            self._U2_=Uup
        else:
            self._E1_=Eup
            self._E2_=Edw
            self._U1_=Uup
            self._U2_=Udw

    @property
    def nk(self):
        '''
        Number of k points of the whole Brillouin zone.
        '''
        return 1 if self.BZ is None else len(self.BZ)

    @property
    def nsp(self):
        '''
        Number of single particle states at each k point.
        '''
        return int(2*self._E1_.shape[1]*self.filling.numerator/self.filling.denominator)

    @property
    def E1(self):
        '''
        The eigenvalues of the projected single particle space.
        '''
        return self._E1_[:,:self.nsp]

    @property
    def E2(self):
        '''
        The eigenvalues of the projected single particle space.
        '''
        return self._E2_[:,:self.nsp]

    @property
    def U1(self):
        '''
        The eigenvectors of the projected single particle space.
        '''
        return self._U1_[:,:,:self.nsp]

    @property
    def U2(self):
        '''
        The eigenvectors of the projected single particle space.
        '''
        return self._U2_[:,:,:self.nsp]

    @property
    def dtype(self):
        '''
        The data type of the basis.
        '''
        return self.U1.dtype

def optrep(operator,k,basis):
    '''
    The matrix representation of an operator.

    Parameters
    ----------
    operator : FOperator or None
        The operator whose matrix representation is wanted.
        ``None`` represents the whole single particle Hamiltonian.
    k : QuantumNumber
        The quantum-number-formed k point.
    basis : FBFMBasis
        The basis of the projected single particle space.

    Returns
    -------
    2d ndarray
        The matrix representation of the operator.
    '''
    nk,nsp=basis.nk,basis.nsp
    permutation=np.array([0]) if basis.BZ is None else np.argsort((basis.BZ-k).sort(history=True)[1])
    if operator is None:
        result=np.zeros((nk,nsp,nsp,nk,nsp,nsp),dtype=basis.dtype)
        for i in xrange(nk):
            for j in xrange(nsp):
                for k in xrange(nsp):
                    result[i,j,k,i,j,k]=basis.E1[permutation[i],j]-basis.E2[i,k]
        return result.reshape((nk*nsp**2,nk*nsp**2))
    elif isinstance(operator,HP.FQuadratic):
        (index1,index2),(seq1,seq2)=operator.indices,operator.seqs
        assert index1.spin==index2.spin and index1.nambu==HP.CREATION and index2.nambu==HP.ANNIHILATION
        result=np.zeros((nk,nk,nsp*nsp,nsp*nsp),dtype=basis.dtype)
        diag=operator.value*(1 if len(k)==0 else np.exp(-1j*np.inner(basis.BZ.kcoord(k),operator.icoord)))*np.identity(nsp,dtype=basis.dtype)
        if index1.spin==(0 if basis.polarization=='up' else 1):
            for i in xrange(nk):
                result[i,i,:,:]=np.kron(np.kron(basis.U1[seq2,i,:].reshape((-1,1)),basis.U1[seq1,i,:].conjugate().reshape((1,-1))),diag)
        else:
            diagsum=(basis.U2[seq1,:,:].conjugate()*basis.U2[seq2,:,:]).sum()*np.identity(nsp,dtype=basis.dtype)
            for i in xrange(nk):
                result[i,i,:,:]=np.kron(diag,diagsum-np.kron(basis.U2[seq1,i,:].conjugate().reshape((-1,1)),basis.U2[seq2,i,:].reshape((1,-1))))
        return result.transpose((0,2,1,3)).reshape((nk*nsp**2,nk*nsp**2))
    elif isinstance(operator,HP.FHubbard):
        assert len(set(operator.seqs))==1
        assert operator.indices[1].replace(nambu=HP.CREATION)==operator.indices[0]
        assert operator.indices[3].replace(nambu=HP.CREATION)==operator.indices[2]
        mhubbard=mhubbard_r4 if basis.dtype==np.float32 else (mhubbard_r8 if basis.dtype==np.float64 else (mhubbard_c4 if basis.dtype==np.complex64 else mhubbard_c8))
        result=mhubbard(operator.value,next(iter(operator.seqs))+1,permutation+1,basis.U1,basis.U2)
        return result.reshape((nk*nsp**2,nk*nsp**2))
    else:
        raise ValueError('optrep error: not supported operator type(%s).'%operator.__class__.__name__)

class FBFM(HP.Engine):
    '''
    Attributes
    ----------
    basis : FBFMBasis
        The basis of the projected single particle space.
    lattice : Lattice
        The lattice of the system.
    config : IDFConfig
        The configuration of the internal degrees of freedom of the system.
    terms : list of Term
        The single particle terms of the system.
    interactions : list of Term
        The interaction terms of the system.
    dtype : np.float64 or np.complex128, etc
        The data type of the matrix representation of the system's Hamiltonian.
    generator : Generator
        The generator of the single particle part of the system.
    igenerator : Generator
        The generator of the interaction part of the system.

    Supported methods:
        =========     ==================================================
        METHODS       DESCRIPTION
        =========     ==================================================
        `FBFMEB`      calculate the energy spectrums of spin excitations
        `FBFMPOS`     calculate the profiles of spin-1-excitation states
        =========     ==================================================
    '''

    def __init__(self,basis=None,lattice=None,config=None,terms=None,interactions=None,dtype=np.complex128,**karg):
        '''
        Constructor.

        Parameters
        ----------
        basis : FBFMBasis
            The basis of the projected single particle space.
        lattice : Lattice
            The lattice of the system.
        config : IDFConfig
            The configuration of the internal degrees of freedom of the system.
        terms : list of Term
            The single particle terms of the system.
        interactions : list of Term
            The interaction terms of the system.
        dtype : np.float64 or np.complex128, etc
            The data type of the matrix representation of the system's Hamiltonian.
        '''
        assert config.priority==FBFM_PRIORITY
        self.basis=basis
        self.lattice=lattice
        self.config=config
        self.terms=terms
        self.interactions=interactions
        self.dtype=dtype
        if self.map is None: self.parameters.update(OrderedDict((term.id,term.value) for term in it.chain(terms,interactions)))
        self.generator=HP.Generator(bonds=lattice.bonds,config=config,table=config.table(mask=['nambu']),terms=terms,dtype=dtype,half=True)
        self.igenerator=HP.Generator(bonds=lattice.bonds,config=config,table=config.table(mask=['spin','nambu']),terms=interactions,dtype=dtype,half=False,order='density')
        self.basis.set(self.spmatrix)

    def spmatrix(self,k=()):
        '''
        The single particle matrix.

        Parameters
        ----------
        k : iterable of float
            The k point.

        Returns
        -------
        2d ndarray
            The single particle matrix.
        '''
        result=np.zeros((len(self.generator.table),len(self.generator.table)),dtype=self.dtype)
        for opt in self.generator.operators.values():
            result[opt.seqs]+=opt.value*(1 if len(k)==0 else np.exp(-1j*np.inner(k,opt.icoord)))
        result+=result.T.conjugate()
        return result

    def update(self,**karg):
        '''
        Update the engine.
        '''
        if len(karg)>0:
            super(FBFM,self).update(**karg)
            karg=self.data(karg)
            self.generator.update(**karg)
            self.igenerator.update(**karg)
            self.basis.set(self.spmatrix)

    @property
    def nmatrix(self):
        '''
        The dimension of the Hilbert space of spin-1 excitations.
        '''
        return self.basis.nk*self.basis.nsp**2

    def matrix(self,k=None,**karg):
        '''
        The matrix representation of the spin excitations.

        Parameters
        ----------
        k : QuantumNumber, optional

        Returns
        -------
        2d ndarray
            The matrix representation of the spin excitations.
        '''
        if len(karg)>0: self.update(**karg)
        result=0
        for operator in it.chain([None],self.igenerator.operators.itervalues()):
            result+=optrep(operator,k,self.basis)
        return result

    def view(self,mode='P',path=None,show=True,suspend=False,close=True):
        '''
        View the single particle energy levels along a path in the k space.

        Parameters
        ----------
        mode : 'P','A'
            'P' for viewing only the projected single particle energy levels;
            'A' for viewing all the single particle energy levels.
        path : str, optional
            The str-formed path.
        show : logical, optional
            True for showing the view and False for not.
        suspend : logical, optional
            True for suspending the view and False for not.
        close : logical, optional
            True for closing the view and False for not.
        '''
        mode=mode.upper()
        assert mode in ('P','A')
        E1=self.basis.E1 if mode=='P' else self.basis._E1_
        E2=self.basis.E2 if mode=='P' else self.basis._E2_
        if path is None:
            assert self.basis.BZ is None
            ks=[0,1]
            e1=np.vstack([E1,E1])
            e2=np.vstack([E2,E2])
        else:
            ks=self.basis.BZ.path(HP.KMap(self.basis.BZ.reciprocals,path),mode='I')
            e1=E1[ks,:]
            e2=E2[ks,:]
        fig,ax=plt.subplots(nrows=1,ncols=2)
        plt.suptitle('%s'%self.tostr(mask=[term.id for term in self.interactions]))
        ax[0].plot(ks,e1)
        ax[1].plot(ks,e2)
        ax[0].set_title('Spin down' if self.basis.polarization=='up' else 'Spin up')
        ax[1].set_title('Spin up' if self.basis.polarization=='up' else 'Spin down')
        if show and suspend: plt.show()
        if show and not suspend: plt.pause(1)
        if close: plt.close()

class EB(HP.EB):
    '''
    Energy spectrums of spin excitations.

    Attributes
    ----------
    ne : integer
        The number of energy spectrums.
    method : 'eigh','eigsh'
        The function used to calculate the spectrums. 'eigh' for `sl.eigh` and 'eigsh' for `HM.eigsh`.
    '''

    def __init__(self,ne=6,method='eigh',**karg):
        '''
        Constructor.

        Parameters
        ----------
        ne : integer, optional
            The number of energy spectrums.
        method : 'eigh','eigsh'
            The function used to calculate the spectrums. 'eigh' for `sl.eigh` and 'eigsh' for `HM.eigsh`.
        '''
        super(EB,self).__init__(**karg)
        self.ne=ne
        self.method=method

def FBFMEB(engine,app):
    '''
    This method calculates the energy spectrums of the spin excitations.
    '''
    path,ne=app.path,min(app.ne or engine.nmatrix,engine.nmatrix)
    if path is not None:
        bz,reciprocals=engine.basis.BZ,engine.lattice.reciprocals
        parameters=list(path('+')) if isinstance(path,HP.BaseSpace) else [{'k':bz[pos]} for pos in bz.path(HP.KMap(reciprocals,path) if isinstance(path,str) else path,mode='I')]
        result=np.zeros((len(parameters),ne+1))
        result[:,0]=path.mesh(0) if isinstance(path,HP.BaseSpace) and path.mesh(0).ndim==1 else np.array(xrange(len(parameters)))
        engine.log<<'%s: '%len(parameters)
        for i,paras in enumerate(parameters):
            engine.log<<'%s%s'%(i,'..' if i<len(parameters)-1 else '')
            m=engine.matrix(**paras)
            result[i,1:]=sl.eigh(m,eigvals_only=True)[:ne] if app.method=='eigh' else HM.eigsh(m,k=ne,return_eigenvectors=False)
        engine.log<<'\n'
    else:
        result=np.zeros((2,ne+1))
        result[:,0]=np.array(xrange(2))
        result[0,1:]=sl.eigh(engine.matrix(),eigvals_only=True)[:ne] if app.method=='eigh' else HM.eigsh(engine.matrix(),k=ne,return_eigenvectors=False)
        result[1,1:]=result[0,1:]
    name='%s_%s'%(engine.tostr(mask=path.tags if isinstance(path,HP.BaseSpace) else ()),app.name)
    if app.savedata: np.savetxt('%s/%s.dat'%(engine.dout,name),result)
    if app.plot: app.figure('L',result,'%s/%s'%(engine.dout,name))

def FBFMPOS(engine,app):
    '''
    This method calculates the profiles of spin-1-excitation states.
    '''
    result=[]
    table=engine.config.table(mask=['spin','nambu'])
    U1,U2,vs=engine.basis.U1,engine.basis.U2,sl.eigh(engine.matrix(k=app.k),eigvals_only=False)[1]
    for i,index in enumerate(sorted(table,key=table.get)):
        result.append([i])
        gs=np.vdot(U2[table[index],:,:].reshape(-1),U2[table[index],:,:].reshape(-1))*(1 if engine.basis.polarization=='up' else -1)
        dw=optrep(HP.FQuadratic(1.0,(index.replace(spin=0,nambu=HP.CREATION),index.replace(spin=0,nambu=HP.ANNIHILATION)),seqs=(table[index],table[index])),app.k,engine.basis)
        up=optrep(HP.FQuadratic(1.0,(index.replace(spin=1,nambu=HP.CREATION),index.replace(spin=1,nambu=HP.ANNIHILATION)),seqs=(table[index],table[index])),app.k,engine.basis)
        for pos in app.ns or (0,):
            result[-1].append((np.vdot(vs[:,pos],up.dot(vs[:,pos]))-np.vdot(vs[:,pos],dw.dot(vs[:,pos]))-gs)*(-1 if engine.basis.polarization=='up' else 1))
    result=np.asarray(result)
    name='%s_%s'%(engine,app.name)
    if app.savedata: np.savetxt('%s/%s.dat'%(engine.dout,name),result)
    if app.plot: app.figure('L',result,'%s/%s'%(engine.dout,name),legend=['Level %s'%n for n in app.ns or (0,)])