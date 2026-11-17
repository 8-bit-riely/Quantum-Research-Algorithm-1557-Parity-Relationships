"""Exact observability, covariance decoding and coupled table operations.

These operate on probability specifications and retained statistics. They do
not evaluate circuits, generate samples, train a model or contact hardware.
"""
from fractions import Fraction
from itertools import combinations
from math import isfinite

from .core import JointTable, exact, parity_sign, require


def mask_for(bits, selected):
    require(len(set(selected))==len(selected) and set(selected)<=set(bits),'Distinct known bit labels required')
    return sum(1 << (len(bits)-1-bits.index(bit)) for bit in selected)


def mask_labels(bits, mask):
    return [bit for i,bit in enumerate(bits) if mask & (1 << (len(bits)-1-i))]


def feature_masks(n, order=2):
    return [mask for degree in range(1,min(n,order)+1) for mask in range(1,1<<n) if mask.bit_count()==degree]


def moment(table, mask):
    require(type(mask) is int and 0<=mask<len(table.probabilities),'Invalid local mask')
    return sum(parity_sign(i&mask)*p for i,p in enumerate(table.probabilities))


def coverage(n, masks, same_shot_covariance=False):
    require(1<=n<=12 and len(set(masks))==len(masks) and all(0<m<1<<n for m in masks),'Distinct nonconstant masks required')
    recovered={0,*masks}
    if same_shot_covariance:
        # Exactly ONE product/XOR step, not transitive closure.
        recovered.update(a^b for a in masks for b in masks)
    return {'variables':n,'nonconstantCoordinates':(1<<n)-1,
            'recoverableNonconstantCoordinates':len(recovered)-1,
            'unobservedCoordinates':(1<<n)-len(recovered),
            'recoverableMasks':sorted(recovered-{0}),
            'hiddenMasks':[m for m in range(1,1<<n) if m not in recovered],
            'fullSameShotCovarianceIncluded':same_shot_covariance}


def rational_rank(matrix):
    if not matrix:
        return 0
    width=len(matrix[0]);require(all(len(row)==width for row in matrix),'Rectangular matrix required')
    work=[[Fraction(v) for v in row] for row in matrix];rank=0
    for column in range(width):
        pivot=next((r for r in range(rank,len(work)) if work[r][column]),None)
        if pivot is None:
            continue
        work[rank],work[pivot]=work[pivot],work[rank]
        divisor=work[rank][column];work[rank]=[v/divisor for v in work[rank]]
        for row in range(rank+1,len(work)):
            scale=work[row][column]
            if scale:
                work[row]=[a-scale*b for a,b in zip(work[row],work[rank])]
        rank+=1
        if rank==len(work):
            break
    return rank


def fixed_pair_geometry(table):
    """Dimension of the exact nonnegative-table face forced by zero pairs."""
    n=len(table.bits);masks=[0,*feature_masks(n,2)]
    forced=set();constraints=[]
    for size in range(1,min(n,2)+1):
        for bits in combinations(table.bits,size):
            values=table.marginal(bits)
            for category,p in enumerate(values):
                if p:
                    continue
                positions=[n-1-table.bits.index(bit) for bit in bits]
                matching=[]
                for word in range(1<<n):
                    sub=0
                    for position in positions:
                        sub=(sub<<1)|((word>>position)&1)
                    if sub==category:
                        matching.append(word);forced.add(word)
                constraints.append({'bits':list(bits),'zeroCategory':format(category,f'0{size}b'),'forcedFullCategories':matching})
    allowed=[i for i in range(1<<n) if i not in forced]
    rank=rational_rank([[parity_sign(i&mask) for i in allowed] for mask in masks])
    return {'forcedZeroCategories':sorted(forced),'allowedCategories':allowed,
            'zeroMarginalConstraints':constraints,'rankIncludingNormalizationOnAllowedFace':rank,
            'affineDimensionOnForcedZeroFace':len(allowed)-rank,
            'scope':'Exact empirical fixed-pair table face, not a population or physical capability bound'}


def direction(table, selected, context=None):
    """Parity adjustment, optionally restricted to a named binary context."""
    context=context or {};require(set(context)<=set(table.bits),'Unknown context label')
    require(not(set(context)&set(selected)),'Context and parity labels must be disjoint')
    require(all(type(v) is int and v in (0,1) for v in context.values()),'Binary context required')
    mask=mask_for(table.bits,selected);require(mask!=0,'Nonempty parity selection required')
    positions={bit:len(table.bits)-1-table.bits.index(bit) for bit in context}
    return tuple(Fraction(parity_sign(i&mask)) if all(((i>>positions[b])&1)==v for b,v in context.items()) else Fraction(0)
                 for i in range(len(table.probabilities)))


def direction_interval(table, vector):
    require(len(vector)==len(table.probabilities) and any(vector) and sum(vector)==0,'Nonzero normalized direction required')
    low=max(-p/v for p,v in zip(table.probabilities,vector) if v>0)
    high=min(-p/v for p,v in zip(table.probabilities,vector) if v<0)
    return low,high


def move(table, vector, epsilon):
    epsilon=Fraction(epsilon);low,high=direction_interval(table,vector)
    require(low<=epsilon<=high,'Direction outside this table\'s valid interval')
    return JointTable(table.bits,tuple(p+epsilon*v for p,v in zip(table.probabilities,vector)))


def covariance_of_means(table, masks, shots):
    require(type(shots) is int and shots>=2,'Known shot count required')
    m={mask:moment(table,mask) for mask in {0,*masks,*(a^b for a in masks for b in masks)}}
    return [m[a] for a in masks], [[(m[a^b]-m[a]*m[b])/(shots-1) for b in masks] for a in masks]


def recover_exact_moments(masks, means, mean_covariance, shots):
    require(len(masks)==len(means)==len(mean_covariance) and all(len(row)==len(masks) for row in mean_covariance),'Covariance dimensions differ')
    require(type(shots) is int and shots>=2,'Known shot count required')
    recovered={0:Fraction(1)}
    def record(mask,value):
        value=Fraction(value)
        require(-1<=value<=1,'Recovered moment outside [-1,1]')
        require(mask not in recovered or recovered[mask]==value,'Covariance recovery paths disagree')
        recovered[mask]=value
    for mask,value in zip(masks,means):
        record(mask,value)
    for i,a in enumerate(masks):
        for j,b in enumerate(masks):
            record(a^b,(shots-1)*Fraction(mean_covariance[i][j])+Fraction(means[i])*Fraction(means[j]))
    return recovered


def recover_archived_moments(masks, means, mean_covariance, shots, tolerance_in_count_units=1e-7):
    """Recover lattice-valued empirical moments from verified float archives."""
    require(type(shots) is int and shots>=2 and len(masks)==len(means)==len(mean_covariance), 'Known sampling convention required')
    require(all(len(row)==len(masks) for row in mean_covariance),'Covariance shape differs')
    recovered={0:Fraction(1)};max_rounding=0.
    def record(mask,value):
        nonlocal max_rounding
        require(isfinite(value),'Nonfinite archived moment')
        scaled=value*shots;numerator=round(scaled);error=abs(scaled-numerator)
        max_rounding=max(max_rounding,error)
        require(error<=tolerance_in_count_units and abs(numerator)<=shots and (shots-numerator)%2==0,'Not a compatible empirical parity moment')
        exact_value=Fraction(numerator,shots)
        require(mask not in recovered or recovered[mask]==exact_value,'Archived recovery paths disagree')
        recovered[mask]=exact_value
    for mask,value in zip(masks,means):
        record(mask,float(value))
    for i,a in enumerate(masks):
        for j,b in enumerate(masks):
            record(a^b,(shots-1)*float(mean_covariance[i][j])+float(means[i])*float(means[j]))
    return recovered,max_rounding


def table_from_moments(bits, physical_moments):
    """Inverse Walsh transform of one selected subset, not quantum tomography."""
    n=len(bits);moments=[]
    for local in range(1<<n):
        physical=sum(1<<bits[n-1-j] for j in range(n) if local&(1<<j))
        require(physical in physical_moments,'Required subset moment is unavailable')
        moments.append(physical_moments[physical])
    probabilities=tuple(sum(parity_sign(i&mask)*moments[mask] for mask in range(1<<n))/(1<<n) for i in range(1<<n))
    return JointTable(tuple(bits),probabilities)
