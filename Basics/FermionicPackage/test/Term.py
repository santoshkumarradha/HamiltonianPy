'''
Fermionic term test.
'''

__all__=['test_fermionic_term']

from HamiltonianPy.Basics.Geometry import *
from HamiltonianPy.Basics.DegreeOfFreedom import *
from HamiltonianPy.Basics.Operator import *
from HamiltonianPy.Basics.Term import *
from HamiltonianPy.Basics.FermionicPackage import *

def test_fermionic_term():
    test_quadratic()
    test_hubbard()

def test_quadratic():
    print 'test_quadratic'
    p1=Point(pid=PID(site=0,scope='WG'),rcoord=[0.0,0.0],icoord=[0.0,0.0])
    p2=Point(pid=PID(site=1,scope='WG'),rcoord=[1.0,0.0],icoord=[0.0,0.0])
    bond=Bond(neighbour=1,spoint=p1,epoint=p2)

    config=Configuration(priority=DEFAULT_FERMIONIC_PRIORITY)
    config[p1.pid]=Fermi(atom=0,norbital=2,nspin=2,nnambu=2)
    config[p2.pid]=Fermi(atom=1,norbital=2,nspin=2,nnambu=2)

    a=QuadraticList(Hopping('t1',1.0,neighbour=1,indexpacks=sigmaz("SP")),Hopping('t2',1,neighbour=1,indexpacks=sigmax("SL")*sigmax("SP")))
    print 'a: %s'%a
    print a.mesh(bond,config)
    b=Onsite('mu1',1.0,neighbour=0,indexpacks=sigmaz("SP"))+Onsite('mu2',1,neighbour=0,indexpacks=sigmaz("SP")*sigmay("OB"))
    print 'b: %s'%b
    print b.mesh(bond,config)
    c=Pairing('delta1',1.0,neighbour=1,indexpacks=sigmaz("SP"))+Pairing('delta2',1,neighbour=1,indexpacks=sigmaz("SP")+sigmay("OB"))
    print 'c: %s'%c
    print c.mesh(bond,config)

    l=Lattice(name="WG",points=[p1,p2])
    table=config.table(nambu=True)
    a=Hopping('t1',1.0,neighbour=1,indexpacks=sigmaz("SP"))
    b=Onsite('mu',1.0,neighbour=0,indexpacks=sigmaz("SP"))
    c=Pairing('delta',1.0,neighbour=1,indexpacks=sigmaz("SP"),modulate=lambda **karg: 1)
    d=a+b+c
    print 'd: %s'%d
    opts=OperatorCollection()
    for bond in l.bonds:
        opts+=d.operators(bond,config,table)
    print 'opts:\n%s'%opts
    print

def test_hubbard():
    print 'test_hubbard'
    p1=Point(PID(site=0,scope="WG"),rcoord=[0.0,0.0],icoord=[0.0,0.0])
    config=Configuration(priority=DEFAULT_FERMIONIC_PRIORITY)
    config[p1.pid]=Fermi(norbital=2,nspin=2,nnambu=1)
    l=Lattice(name="WG",points=[p1])
    table=config.table(nambu=True)
    a=+Hubbard('UUJJ',[20.0,12.0,5.0,5.0])
    print 'a: %s'%a
    opts=OperatorCollection()
    for bond in l.bonds:
        opts+=a.operators(bond,config,table)
    print 'opts:\n%s'%opts
    print