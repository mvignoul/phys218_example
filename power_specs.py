#!/usr/bin/env python
# vim: set fileencoding=UTF-8 :

"""
Various flux derivative stuff
Edited to remove all errors 'E' and warnings 'W'. Other non-essential messages were ignored.
Warnings of the form W0621 were also ignored.
"""

import numpy as np
import math
#import smooth
import scipy.interpolate
import sys
import matplotlib.pyplot as plt
import matplotlib.backends
import re
import ast

class DataError(Exception):
    def __init__(self, value):
        self.value = value
        Exception.__init__(self, value)
    def __str__(self):
        return repr(self.value)

def smooth(data, window_len, window):
    """ Smooth data (code modified from SciPy Cookbook 1D smooth) """
    if data.ndim != 1:
        raise ValueError("smooth only accepts 1 dimension arrays.")
    if data.size < window_len:
        raise ValueError("Input vector needs to be bigger than window size.")
    if window_len<3:
        return data
    s=np.r_[data[window_len-1:0:-1],data,data[-2:-window_len-1:-1]]
    if window == 'flat': #moving average
        w=np.ones(window_len,'d')
    else:
        w=ast.literal_eval('np.'+window+'(window_len)')
    y=np.convolve(w/w.sum(),s,mode='valid')
    return y

def smooth_rebin(data, xaxis,newx=np.array([]), smoothing=11):
    """ Smooth and rebin dat points """
    #Window_len of 9-13 seems about right; 7 is still pretty noisy, and higher than 13 
    #tends to start changing the shape of the curve.
    smoothed = smooth(data,window_len=smoothing,window='kaiser')
    if np.size(newx) > 0:
        intp=scipy.interpolate.InterpolatedUnivariateSpline(np.log(xaxis),smoothed)
        newdata=intp(np.log(newx))
        return newdata
    else:
        return smoothed

def wheref(array, value):
    """ A where function to find where a floating point value is equal to another"""
     #Floating point inaccuracy.
    eps=1e-7
    return np.where((array > value-eps)*(array < value+eps))

def rebin(data, xaxis,newx):
    """Just rebins the data"""
    if newx[0] < xaxis[0] or newx[-1]> xaxis[-1]:
        raise ValueError("A value in newx is beyond the interpolation range")
    intp=scipy.interpolate.InterpolatedUnivariateSpline(np.log(xaxis),data)
    newdata=intp(np.log(newx))
    return newdata

def save_figure(path):
    """Saves the figure, automatically determining file extension"""
    bk=matplotlib.backends.backend
    if path == "":
        return
    elif bk == 'TkAgg' or bk == 'Agg' or bk == 'GTKAgg':
        path = path+".png"
    elif bk == 'PDF' or bk == 'pdf':
        path = path+".pdf"
    elif bk == 'PS' or bk == 'ps':
        path = path+".ps"
    return plt.savefig(path)

def corr_table(table, dvecs,table_name):
    """Little function to adjust a table so it has a different central value"""
    new=np.array(table)
    new[12:,:] = table[12:,:]+2*table[0:12,:]*dvecs
    pkd="/home/spb41/cosmomc-src/cosmomc/data/lya-interp/"
    np.savetxt(pkd+table_name,new,("%1.3g","%1.3g","%1.3g","%1.3g","%1.3g","%1.3g","%1.3g","%1.3g","%1.3g","%1.3g","%1.3g"))
    return new

class power_spec:
    """ A class to be derived from by flux and matter power_spec classes. Stores various helper methods."""
    # Snapshots
    Snaps=()
    #SDSS redshift bins.
    Zz=np.array([1.0])
    #SDSS kbins, in s/km units.
    sdsskbins=np.array([1.0])
    # Omega_matter
    om=0.267
    #Hubble constant
    H0=0.71
    #Boxsize in Mpc/h
    box=60.0
    #Size of the best-fit box, for testing varying boxsize 
    bfbox=60.0
    #Some paths
    knotpos=np.array([1.0])
    base=""
    pre=""
    suf=""
    ext=""
    #For plotting
    ymin=0.8
    ymax=1.2
    figprefix="/figure"
    def __init__(self, Snaps=("snapshot_000", "snapshot_001","snapshot_002","snapshot_003","snapshot_004","snapshot_005","snapshot_006","snapshot_007","snapshot_008","snapshot_009","snapshot_010","snapshot_011"),
         Zz=np.array([4.2,4.0,3.8,3.6,3.4,3.2,3.0,2.8,2.6,2.4,2.2,2.0]),
         sdsskbins=np.array([0.00141,0.00178,0.00224,0.00282,0.00355,0.00447,0.00562,0.00708,0.00891,0.01122,0.01413,0.01778]),
         knotpos=np.array([0.07,0.15,0.475, 0.75, 1.19, 1.89,4,25]), om=0.267, H0=0.71,box=60.0,
         base="/home/spb41/Lyman-alpha/MinParametricRecon/runs/",suf="/", ext=".txt"):
        if len(Snaps) != np.size(Zz):
            raise DataError("There are "+str(len(Snaps))+" snapshots, but "+str(np.size(Zz))+"redshifts given.")
        self.Snaps=Snaps
        self.Zz=Zz
        self.sdsskbins=sdsskbins
        self.om=om
        self.H0=H0
        self.box=box
        self.knotpos=knotpos*H0
        self.base=base
        self.suf=suf
        self.ext=ext
        return 

    
    def loadpk(self, path,box):
        """Load a Pk"""
        # Needed a loadpk member function, so this is from the flux_pow class.
        # power_spec class exists as an ancestor to the flux and matter classes, so it shouldn't really
        #   matter what we define loadpk to be here - each class has its own function
        #Adjust Fourier convention.
        flux_power=np.loadtxt(self.base+path)
        scale=self.H0/box
        k=(flux_power[1:,0]-0.5)*scale*2.0*math.pi
        PF=flux_power[1:,1]/scale
        return (k, PF)

    def GetZ(self, snap):
        """ Get redshift associated with a snapshot """
        ind=np.where(np.array(self.Snaps) == snap)
        if np.size(ind):
            return self.Zz[ind]
        else:
            raise DataError(str(snap)+" does not exist!") 
    
    def GetSnap(self, redshift):
        """ Get snapshot associated with a redshift """
        ind=wheref(self.Zz, redshift)
        if np.size(ind):
            return str(np.asarray(self.Snaps)[ind][0])
        else:
            raise DataError("No snapshot at redshift "+str(redshift))

    def GetSDSSkbins(self, redshift):
        """Get the k bins at a given redshift in h/Mpc units"""
        return self.sdsskbins*self.Hubble(redshift)/(1.0+redshift)
#Corr is /sqrt(self.H0)...

    def Getkbins(self):
        """Get the kbins to interpolate onto"""
    # power_spec class does not have a kbins member, so we use the definition of Getkbins() from 
    #   the flux_pdf child class to avoid adding an attribute to the class
        return np.arange(0,20,1)+0.5
    
    def Hubble(self, zz):
        """ Hubble parameter. Hubble(Redshift) """
        return 100*self.H0*math.sqrt(self.om*(1+zz)**3+(1-self.om))
    #Conversion factor between s/km and h/Mpc is (1+z)/H(z)
    
    def loaddata(self, file, box):
        """ Do correct units conversion to return k and one-d power """
        #Adjust Fourier convention.
        flux_power=np.loadtxt(file)
        scale=self.H0/box
        k=flux_power[1:,0]*scale*2.0*math.pi
        PF=flux_power[1:,1]/scale
        return (k, PF)
    
    def plot_z(self,Knot,redshift,title="",ylabel="", legend=True):
        """ Plot comparisons between a bunch of sims on one graph 
        plot_z(Redshift, Sims to use ( eg, A1.14). 
        Note this will clear current figures."""
        #Load best-fit
        (simk,BFPk)=self.loadpk(Knot.bstft+self.suf+self.pre+self.GetSnap(redshift)+self.ext,self.bfbox)
        #Setup figure plot.
        ind=wheref(self.Zz, redshift)
        plt.figure(ind[0][0])
        plt.clf()
        if title != '':
            plt.title(title+" at z="+str(redshift))
        plt.ylabel(ylabel)
        plt.xlabel(r"$k\; (\mathrm{Mpc}^{-1})$")
        line=np.array([])
        legname=np.array([])
        for sim in Knot.names:
            (k,Pk)=self.loadpk(sim+self.suf+self.pre+self.GetSnap(redshift)+self.ext,self.box)
            oi = np.where(simk <= k[-1])
            ti = np.where(simk[oi] >= k[0])
            relP=rebin(Pk, k, simk[oi][ti])
            relP=relP/rebin(BFPk, simk, simk[oi][ti])
#             relP=smooth_rebin(relP,simk)
            line=np.append(line, plt.semilogx(simk[oi][ti]/self.H0,relP,linestyle="-"))
            legname=np.append(legname,sim)
        if legend:
            plt.legend(line,legname)
            plt.semilogx(self.knotpos,np.ones(len(self.knotpos)),"ro")
        plt.ylim(self.ymin,self.ymax)
        plt.xlim(simk[0]*0.8, 10)
        return
    
    def plot_all(self, Knot,zzz=np.array([]), out=""):
        """ Plot a whole suite of snapshots: plot_all(Knot, outdir) """
        if np.size(zzz) == 0:
            zzz=self.Zz    #lolz
        for z in zzz:
            self.plot_z(Knot,z)
            if out != "":
                save_figure(out+self.figprefix+str(z))
        return
    
    def plot_power(self,path, redshift,colour="black",camb_filename=""):
        """ Plot absolute power spectrum, not relative"""
    #def plot_power(self,path, redshift,colour="black"):
        # define some placeholder thing to avoid warnings that cascaded back
        camb_filename = camb_filename[:len(camb_filename)]
        (k_g,Pk_g)=self.loadpk(path+self.suf+self.pre+self.GetSnap(redshift)+self.ext,self.box) 
        plt.loglog(k_g,Pk_g, color=colour)
        plt.xlim(0.01,k_g[-1]*1.1)
        plt.ylabel("P(k) /(h-3 Mpc3)")
        plt.xlabel("k /(h MPc-1)")
        plt.title("Power spectrum at z="+str(redshift))
        return(k_g, Pk_g)
    
    def plot_power_all(self, Knot,zzz=np.array([]), out=""):
        """ Plot absolute power for all redshifts """
        if np.size(zzz) == 0:
            zzz=self.Zz    #lolz
        for z in zzz:
            ind=wheref(self.Zz, z)
            plt.figure(ind[0][0])
            for sim in Knot.names:
                self.plot_power(sim,z)
            if out != "":
                save_figure(out+self.figprefix+str(z))
        return

    def plot_compare_two(self, one, onebox, two,twobox,colour=""):
        """ Compare two power spectra directly. Smooths result. 
        plot_compare_two(first P(k), second P(k))"""
        (onek,oneP)=self.loadpk(one,onebox)
        (twok,twoP)=self.loadpk(two,twobox)
        onei = np.where(onek <= twok[-1])
        twoi= np.where (onek[onei] >= twok[0])
        relP=rebin(twoP, twok, onek[onei][twoi])
        relP=relP/rebin(oneP, onek, onek[onei][twoi])
        onek=onek[onei][twoi]
#         relP=smooth_rebin(relP,onek)
        plt.title("Relative Power spectra "+one+" and "+two)
        plt.ylabel(r"$P_2(k)/P_1(k)$")
        plt.xlabel(r"$k\; (h\,\mathrm{Mpc}^{-1})$")
        if colour == "":
            line=plt.semilogx(onek,relP)
        else:
            line=plt.semilogx(onek,relP,color=colour)
        plt.semilogx(self.knotpos,np.ones(len(self.knotpos)),"ro")
        ind=np.where(onek < 10)
        plt.ylim(min(relP[ind])*0.98,max(relP[ind])*1.01)
        plt.xlim(onek[0]*0.8, 10)
        return line

    def compare_two(self, one, two,redshift):
        """Get the difference between two simulations on scales probed by 
        the SDSS power spectrum"""
        (onek,oneP)=self.loadpk(one,self.bfbox)
        (twok,twoP)=self.loadpk(two,self.box)
        onei = np.where(onek <= twok[-1])
        twoi= np.where (onek[onei] >= twok[0])
        relP=rebin(twoP, twok, onek[onei][twoi])
        relP=relP/rebin(oneP, onek, onek[onei][twoi])
        onek=onek[onei][twoi]
        sdss=self.GetSDSSkbins(redshift)
        relP_r=np.ones(np.size(sdss))
        ind = np.where(sdss > onek[0])
        relP_r[ind]=rebin(relP,onek,sdss[ind])
        return relP_r

    def compare_two_table(self,onedir, twodir):
        """Do the above 12 times to get a correction table"""
        nk=np.size(self.sdsskbins)
        nz=np.size(self.Zz)-1
        table=np.empty([nz,nk])
        for i in np.arange(0,nz):
            sim=self.pre+self.GetSnap(self.Zz[i])+self.ext
            table[-1-i,:]=self.compare_two(onedir+sim,twodir+sim,self.Zz[i])
        return table

    def plot_compare_two_sdss(self, onedir, twodir, zzz=np.array([]), out="", title="", ylabel="", ymax=0,ymin=0, colour="",legend=False):
        """ Plot a whole redshift range of relative power spectra on the same figure.
            plot_all(onedir, twodir)
            Pass onedir and twodir as relative to basedir.
            ie, for default settings something like 
            best-fit/flux-power/"""
        if np.size(zzz) == 0:
            zzz=self.Zz    #lolz
        line=np.array([])
        legname=np.array([])
        sdss=self.sdsskbins
        plt.xlabel(r"$k_v\; (s\,\mathrm{km}^{-1})$")
        for z in zzz:
            sim=self.pre+self.GetSnap(z)+self.ext
            Pk=self.compare_two(onedir+sim,twodir+sim,z)
            if colour == "":
                line=np.append(line, plt.semilogx(sdss,Pk))
            else:
                line=np.append(line, plt.semilogx(sdss,Pk,color=colour))
            legname=np.append(legname,"z="+str(z))
        plt.title(title)
        if ylabel != "":
            plt.ylabel(ylabel)
        if legend:
            plt.legend(line, legname,bbox_to_anchor=(0., 0, 1., .25), loc=3,ncol=3, mode="expand", borderaxespad=0.)
        if ymax != 0 and ymin !=0:
            plt.ylim(ymin,ymax)
        plt.xlim(sdss[0],sdss[-1])
        plt.xticks(np.array([sdss[0],3e-3,5e-3,0.01,sdss[-1]]),("0.0014","0.003","0.005","0.01","0.0178"))
        if out != "":
            save_figure(out)
        return plt.gcf()

    def plot_compare_two_all(self, onedir, twodir, zzz=np.array([]), out="", title="", ylabel="", ymax=0,ymin=0, colour="",legend=False):
        """ Plot a whole redshift range of relative power spectra on the same figure.
            plot_all(onedir, twodir)
            Pass onedir and twodir as relative to basedir.
            ie, for default settings something like 
            best-fit/flux-power/
            onedir uses bfbox, twodir uses box"""
        if np.size(zzz) == 0:
            zzz=self.Zz    #lolz
        line=np.array([])
        legname=np.array([])
        for z in zzz:
            line=np.append(line, self.plot_compare_two(onedir+self.pre+self.GetSnap(z)+self.ext,self.bfbox,twodir+self.pre+self.GetSnap(z)+self.ext,self.box,colour))
            legname=np.append(legname,"z="+str(z))  
        if title == "":
            plt.title("Relative Power spectra "+onedir+" and "+twodir)
        else:
            plt.title(title)
        if ylabel != "":
            plt.ylabel(ylabel)
        if legend:
            plt.legend(line, legname,bbox_to_anchor=(0., 0, 1., .25), loc=3,ncol=3, mode="expand", borderaxespad=0.)
        if ymax != 0 and ymin !=0:
            plt.ylim(ymin,ymax)
        if out != "":
            save_figure(out)
        return plt.gcf()
    
    def GetFlat(self,direc, si=0.0):
        """Get a power spectrum in the flat format we use
           for inputting some cosmomc tables"""
        Pk_sdss=np.empty([11, 12])
        #Note this omits the z=2.0 bin
        #SiIII corr now done on the fly in lya_sdss_viel.f90
        for i in np.arange(0,np.size(self.Snaps)-1):
            scale=self.Hubble(self.Zz[i])/(1.0+self.Zz[i])
            (k,Pk)=self.loadpk(direc+self.Snaps[i]+self.ext, self.box)
            Fbar=math.exp(-0.0023*(1+self.Zz[i])**3.65)
            a=si/(1-Fbar)
            #The SiIII correction is kind of oscillatory, so we want 
            #to average over the whole interval being probed.
            sdss=self.sdsskbins
            kmids=np.zeros(np.size(sdss)+1)
            sicorr=np.empty(np.size(sdss))
            for j in np.arange(0,np.size(sdss)-1):
                kmids[j+1]=math.exp((math.log(sdss[j+1])+math.log(sdss[j]))/2.)
            #Final segment should make no difference
            kmids[-1]=2*math.pi/2271+kmids[-2]
            #Near zero bad things will happen
            sicorr[0]=1+a**2+2*a*math.cos(2271*sdss[0])
            for j in np.arange(1,np.size(sdss)):
                sicorr[j]=1+a**2+2*a*(math.sin(2271*kmids[j+1])-math.sin(2271*kmids[j]))/(kmids[j+1]-kmids[j])/2271
            sdss=self.GetSDSSkbins(self.Zz[i])
            Pk_sdss[-i-1,:]=rebin(Pk, k, sdss)*scale*sicorr
        return Pk_sdss

    def GetDiff(self,dir1,dir2,onebox,twobox):
        """Gets the difference between two power spectra, in arbitrary directories, with arbitrary box sizes"""
        diff=np.zeros([self.Zz.size,self.GetSDSSkbins(3.0).size])
        i=0
        for z in self.Zz:
            (onek,oneP)=self.loadpk(dir1+self.pre+self.GetSnap(z)+self.ext,onebox)
            (twok,twoP)=self.loadpk(dir2+self.pre+self.GetSnap(z)+self.ext,twobox)
            onei = np.where(onek <= twok[-1])
            twoi= np.where (onek[onei] >= twok[0])
            relP=rebin(twoP, twok, onek[onei][twoi])
            relP=relP/rebin(oneP, onek, onek[onei][twoi])
            onek=onek[onei][twoi]
            relP=smooth_rebin(relP,onek,self.GetSDSSkbins(z))
            i=i+1
            diff[-i,:]=relP
        diff=np.transpose(diff)
        return diff
    
    def calc_z(self, redshift,s_knot, kbins):
        """ Calculate the flux derivatives for a single redshift
            Output: (kbins d2P...kbins dP (flat vector of length 2xkbins))"""
        #Array to store answers.
        #Format is: k x (dP, d²P, χ²)
        kbins=np.array(kbins)
        nk=np.size(kbins)
        snap=self.GetSnap(redshift)
        results=np.zeros(2*nk)
        if np.size(s_knot.qvals) > 0: 
            results = np.zeros(4*nk)
        pdifs=s_knot.pvals-s_knot.p0
        qdifs=np.array([])
        #If we have somethign where the parameter is redshift-dependent, eg, gamma.
        if np.size(s_knot.p0) > 1:
            i=wheref(redshift, self.Zz)
            pdifs = s_knot.pvals[:,i]-s_knot.p0[i]
            if np.size(s_knot.qvals) > 0:
                qdifs=s_knot.qvals[:,i] - s_knot.q0[i]
        npvals=np.size(pdifs)
        #Load the data
        (k,PFp0)=self.loadpk(s_knot.bstft+self.suf+snap+self.ext,s_knot.bfbox)
        #This is to rescale by the mean flux, for generating mean flux tables.
        ###
        #tau_eff=0.0023*(1+redshift)**3.65
        #tmin=0.2*((1+redshift)/4.)**2
        #tmax=0.5*((1+redshift)/4.)**4
        #teffs=tmin+s_knot.pvals*(tmax-tmin)/30.
        #pdifs=teffs/tau_eff-1.
        ###
        PowerFluxes=np.zeros((npvals,np.size(k)))
        for i in np.arange(0,np.size(s_knot.names)):
            (k,PowerFluxes[i,:])=self.loadpk(s_knot.names[i]+self.suf+snap+self.ext, s_knot.bfbox)
        #So now we have an array of data values, which we want to rebin.
        ind = np.where(kbins >= k[0])
        difPF_rebin=np.ones((npvals,np.size(kbins)))
        for i in np.arange(0, npvals):
            difPF_rebin[i,ind]=rebin(PowerFluxes[i,:]/PFp0,k,kbins[ind])
            #Set the things beyond the range of the interpolator 
            #equal to the final value.
            if ind[0][0] > 0:
                difPF_rebin[i,0:ind[0][0]]=difPF_rebin[i,ind[0][0]]
        #So now we have an array of data values. 
        #Pass each k value to flux_deriv in turn.       
        for k in np.arange(0,np.size(kbins)):
            #Format of returned data is:
            # y = ax**2 + bx + cz**2 +dz +e xz
            # derives = (a,b,c,d,e)
            derivs=self.flux_deriv(difPF_rebin[:,k], pdifs,qdifs)
            results[k]=derivs[0]
            results[nk+k]=derivs[1]
            if np.size(derivs) > 2:
                results[2*nk+k]=derivs[2]
                results[3*nk+k]=derivs[3]
        return results
    
    def calc_all(self, s_knot,kbins):
        """ Calculate the flux derivatives for all redshifts 
        Input: Sims to load, parameter values, mean parameter value
        Output: (2*kbins) x (zbins)"""
        flux_derivatives=np.zeros((2*np.size(kbins),np.size(self.Zz)))
        if np.size(s_knot.qvals) > 1:
            flux_derivatives=np.zeros((4*np.size(kbins),np.size(self.Zz)))
        #Call flux_deriv_const_z for each redshift. 
        for i in np.arange(0,np.size(self.Zz)):
            flux_derivatives[:,i]=self.calc_z(self.Zz[i], s_knot,kbins)
        return flux_derivatives
        
    def flux_deriv(self, PFdif, pdif, qdif=np.array([])):
        """Calculate the flux-derivative for a single redshift and k bin"""
        pdif=np.ravel(pdif)
        if np.size(pdif) != np.size(PFdif):
            raise DataError(str(np.size(pdif))+" parameter values, but "+str(np.size(PFdif))+" P_F values")
        if np.size(pdif) < 2:
            raise DataError(str(np.size(pdif))+" pvals given. Need at least 2.")
        PFdif=PFdif-1.0
        if np.size(qdif) > 2:
            qdif=np.ravel(qdif)
            mat=np.vstack([pdif**2, pdif, qdif**2, qdif] ).T
        else:
            mat=np.vstack([pdif**2, pdif] ).T
        #(derivs, residues,rank, sing)=np.linalg.lstsq(mat, PFdif)
        derivs = np.linalg.lstsq(mat, PFdif)
        return derivs[0]

    
    def Get_Error_z(self, Sim, bstft,box, derivs, params, redshift,qarams=np.empty([])):
        """ Get the error on one test simulation at single redshift """
        #Need to load and rebin the sim. 
        (k, test)=self.loadpk(Sim+self.suf+self.GetSnap(redshift)+self.ext, box)
        (k,bf)=self.loadpk(bstft+self.suf+self.GetSnap(redshift)+self.ext,box)
        kbins=self.Getkbins()
        ind = np.where(kbins >= 1.0*2.0*math.pi*self.H0/box)
        test2=np.ones(np.size(kbins))
        test2[ind]=rebin(test/bf,k,kbins[ind])#
        if ind[0][0] > 0:
            test2[0:ind[0][0]]=test2[ind[0][0]]
        if np.size(qarams) > 0:
            guess=derivs.GetPF(params, redshift,qarams)+1.0
        else:
            guess=derivs.GetPF(params, redshift)+1.0
        return np.array((test2/guess))[0][0]
    
    def plot_error_sdss(self, Sim, bstft, box, derivs, params,qarams=np.array([]),zzz=np.array([]),colour="",ylabel="",title="",ymax=0, ymin=0, legend=False):
        """ Make an interpolation error plot"""
        line=np.array([])
        legname=np.array([])
        sdss=self.sdsskbins
        if np.size(zzz) == 0:
            zzz=self.Zz
        for zz in zzz:
            err=self.Get_Error_z(Sim,bstft,box,derivs,params,zz,qarams)
            sdmpc=self.GetSDSSkbins(zz)
            err=rebin(err, self.Getkbins(),sdmpc)
            #Rebin onto SDSS kbins.
            if colour != "":
                line=np.append(line,plt.semilogx(sdss,err,color=colour))
            else:
                line=np.append(line,plt.semilogx(sdss,err))
            legname=np.append(legname,"z="+str(zz))
        if title != "":
            plt.title(title)
        if ylabel != "":
            plt.ylabel(ylabel)
        plt.xlabel(r"$k_v\; (\mathrm{s}\,\mathrm{km}^{-1})$")
        if ymax != 0 and ymin !=0:
            plt.ylim(ymin,ymax)
        plt.xlim(sdss[0], sdss[-1])
        plt.xticks(np.array([sdss[0],3e-3,5e-3,0.01,sdss[-1]]),("0.0014","0.003","0.005","0.01","0.0178"))
        if legend:
            plt.legend(line, legname,bbox_to_anchor=(0., 0, 1., .25), loc=3,ncol=3, mode="expand", borderaxespad=0.)

    def plot_error_all(self, Sim, bstft, box, derivs, params,zzz=np.array([]),colour="",ylabel="",title="",ymax=0, ymin=0, legend=False):
        """ Make an interpolation error plot"""
        line=np.array([])
        legname=np.array([])
        if np.size(zzz) == 0:
            zzz=self.Zz
        for zz in zzz:
            err=self.Get_Error_z(Sim,bstft, box,derivs,params,zz)
            if colour != "":
                line=np.append(line,plt.semilogx(self.Getkbins(),err,color=colour))
            else:
                line=np.append(line,plt.semilogx(self.Getkbins(),err))
            legname=np.append(legname,"z="+str(zz))  
        if title != "":
            plt.title(title)
        if ylabel != "":
            plt.ylabel(ylabel)
        plt.xlabel(r"$k\; (h\,\mathrm{Mpc}^{-1})$")
        plt.semilogx(self.knotpos,np.ones(len(self.knotpos)),"ro")
        if ymax != 0 and ymin !=0:
            plt.ylim(ymin,ymax)
        plt.xlim(self.Getkbins()[0]*0.95, 4)
        if legend:
            plt.legend(line, legname,bbox_to_anchor=(0., 0, 1., .25), loc=3,ncol=3, mode="expand", borderaxespad=0.)

class flux_pow(power_spec):
    """ A class written to store the various methods related to calculating of the flux derivatives and plotting of the flux power spectra"""
    figprefix="/flux-figure"
    kbins=np.array([])
    def __init__(self, Snaps=("snapshot_000", "snapshot_001","snapshot_002","snapshot_003","snapshot_004","snapshot_005","snapshot_006","snapshot_007","snapshot_008","snapshot_009","snapshot_010","snapshot_011"),
         Zz=np.array([4.2,4.0,3.8,3.6,3.4,3.2,3.0,2.8,2.6,2.4,2.2,2.0]),
         sdsskbins=np.array([0.00141,0.00178,0.00224,0.00282,0.00355,0.00447,0.00562,0.00708,0.00891,0.01122,0.01413,0.01778]),
         knotpos=np.array([0.07,0.15,0.475, 0.75, 1.19, 1.89,4,25]), om=0.266, H0=0.71,box=60.0,kmax=4.0,
         base="/home/spb41/Lyman-alpha/MinParametricRecon/runs/",bf="best-fit/",suf="flux-power/", ext="_flux_power.txt"):
        power_spec.__init__(self, Snaps,Zz,sdsskbins,knotpos, om, H0,box,base,suf, ext)
        #(k_bf,Pk_bf)= self.loadpk(bf+suf+"snapshot_000"+self.ext,self.bfbox)
        k_bf = self.loadpk(bf+suf+"snapshot_000"+self.ext,self.bfbox)
        ind=np.where(k_bf[0] <= kmax)
        self.kbins=k_bf[0][ind]

    def plot_z(self,Knot,redshift,title="Relative Flux Power",ylabel=r"$\mathrm{P}_\mathrm{F}(k,p)\,/\,\mathrm{P}_\mathrm{F}(k,p_0)$", legend=True):
        power_spec.plot_z(self,Knot,redshift,title,ylabel,legend)
        if legend:
            kbins=self.GetSDSSkbins(redshift)
            plt.axvspan(kbins[0], kbins[-1], color="#B0B0B0")
        plt.ylim(self.ymin,self.ymax)
        plt.xlim(self.kbins[0]*0.8, 10)

    def smooth_rebin(self, inarr,k,newk):
        """Wrapper around smooth_rebin to allow us not to do it."""           
        return smooth_rebin(inarr, k, newk)
    
    def Getkbins(self):
        """Get the kbins to interpolate onto"""
        return self.kbins

    def MacDonaldPF(self,sdss, zz):
        """Load the SDSS power spectrum"""
        psdss=sdss[np.where(sdss[:,0] == zz)][:,1:3]
        fbar=math.exp(-0.0023*(1+zz)**3.65)
        #multiply by the hubble parameter to be in 1/(km/s)
        scale=self.Hubble(zz)/(1.0+zz)
        PF=psdss[:,1]*fbar**2/scale
        k=psdss[:,0]*scale
        return (k, PF)

    def loadpk(self, path,box):
        """Load a Pk. Different function due to needing to be different for each class"""
        #Adjust Fourier convention.
        flux_power=np.loadtxt(self.base+path)
        scale=self.H0/box
        k=(flux_power[1:,0]-0.5)*scale*2.0*math.pi
        PF=flux_power[1:,1]/scale
        return (k, PF)


class matter_pow(power_spec):
    """ A class to plot matter power spectra """
    ob=0.0
    #For plotting
    ymin=0.4
    ymax=1.6
    figprefix="/matter-figure"
    def __init__(self, Snaps=("snapshot_000", "snapshot_001","snapshot_002","snapshot_003","snapshot_004","snapshot_005","snapshot_006","snapshot_007","snapshot_008","snapshot_009","snapshot_010","snapshot_011"),
         Zz=np.array([4.2,4.0,3.8,3.6,3.4,3.2,3.0,2.8,2.6,2.4,2.2,2.0]),
         sdsskbins=np.array([0.00141,0.00178,0.00224,0.00282,0.00355,0.00447,0.00562,0.00708,0.00891,0.01122,0.01413,0.01778]),
         knotpos=np.array([0.07,0.15,0.475, 0.75, 1.19, 1.89,4,25]), om=0.266,ob=0.0449, H0=0.71,box=60.0,
         base="/home/spb41/Lyman-alpha/MinParametricRecon/runs/",suf="matter-power/", ext=".0", matpre="PK-by-"):
        power_spec.__init__(self, Snaps,Zz,sdsskbins,knotpos, om, H0,box,base,suf,ext)
        self.ob=ob
        self.pre=matpre

    def plot_z(self,Knot,redshift,title="Relative Matter Power",ylabel=r"$\mathrm{P}(k,p)\,/\,\mathrm{P}(k,p_0)$",legend=True):
        power_spec.plot_z(self,Knot,redshift,title,ylabel,legend)

    def loadpk(self, path,box):
        """Load a Pk. Different function due to needing to be different for each class"""
        #Load baryon P(k)
        matter_power=np.loadtxt(self.base+path)
        scale=self.H0/box
        #Adjust Fourier convention.
        simk=matter_power[1:,0]*scale*2.0*math.pi
        Pkbar=matter_power[1:,1]/scale**3
        #Load DM P(k)
        matter_power=np.loadtxt(self.base+re.sub("by","DM",path))
        PkDM=matter_power[1:,1]/scale**3
        Pk=(Pkbar*self.ob+PkDM*(self.om-self.ob))/self.om
        return (simk,Pk)

    def plot_power(self,path, redshift,colour="black",camb_filename=""):
        """ Plot absolute power spectrum, not relative"""
        (k_g, Pk_g)=power_spec.plot_power(self,path,redshift,colour,camb_filename)
        sigma=2.0
        pkg=np.loadtxt(self.base+path+self.suf+self.pre+self.GetSnap(redshift)+self.ext)
        samp_err=pkg[1:,2]
        sqrt_err=np.array(np.sqrt(samp_err))
        plt.loglog(k_g,Pk_g*(1+sigma*(2.0/sqrt_err+1.0/samp_err)),linestyle="-.",color="black")
        plt.loglog(k_g,Pk_g*(1-sigma*(2.0/sqrt_err+1.0/samp_err)),linestyle="-.",color="black")
        if camb_filename != "":
            camb=np.loadtxt(camb_filename)
            #Adjust Fourier convention.
            k=camb[:,0]*self.H0
            #NOW THERE IS NO h in the T anywhere.
            Pk=camb[:,1]
            plt.loglog(k/self.H0, Pk, linestyle="--")
        plt.xlim(0.01,k_g[-1]*1.1)
        return(k_g, Pk_g)

class flux_pdf(power_spec):
    """The PDF is an instance of the power_spec class. Perhaps poor naming"""
    def __init__(self, Snaps=("snapshot_006","snapshot_007","snapshot_008","snapshot_009","snapshot_010","snapshot_011"),
         Zz=np.array([3.0,2.8,2.6,2.4,2.2,2.0]),
         sdsskbins=np.arange(0,20),
         knotpos=np.array([]), om=0.266, H0=0.71,box=48.0,
         # ob=0.0449,
         base="/home/spb41/Lyman-alpha/MinParametricRecon/runs/",suf="flux-pdf/", ext="_flux_pdf.txt",):
        power_spec.__init__(self, Snaps,Zz,sdsskbins,knotpos, om, H0,box,base,suf,ext)

    def loadpk(self, path, box):
        flux_pdf = np.loadtxt(self.base+path)
        return(flux_pdf[:,0], flux_pdf[:,1])
    
    def plot_compare_two(self, one, onebox, two,twobox,colour=""):
        """ Compare two power spectra directly. Smooths result. 
            plot_compare_two(first P(k), second P(k))"""
        (onek,oneP)=self.loadpk(one,onebox)
        #(twok,twoP)=self.loadpk(two,twobox)
        twoP=self.loadpk(two,twobox)
        relP=oneP/twoP[1]
        plt.title("Relative flux PDF "+one+" and "+two)
        plt.ylabel(r"$F_2(k)/F_1(k)$")
        plt.xlabel(r"$Flux$")
        line=plt.semilogy(onek,relP)
        return line
    
    def plot_power(self,path, redshift,colour="black",camb_filename=""):
        """ Plot absolute power spectrum, not relative"""
        (k,Pdf)=self.loadpk(path+self.suf+self.pre+self.GetSnap(redshift)+self.ext,self.box)  
        plt.semilogy(k,Pdf, color="black", linewidth="1.5")
        plt.ylabel("P(k) /(h-3 Mpc3)")
        plt.xlabel("k /(h MPc-1)")
        plt.title("PDF at z="+str(redshift))
        return(k, Pdf)
        
    def smooth_rebin(self,inarr):
        """Wrapper around smooth_rebin to allow us not to do it."""     
        return inarr
    
    def calc_z(self, redshift,s_knot,kbins):
        """ Calculate the flux derivatives for a single redshift
            Output: (kbins d2P...kbins dP (flat vector of length 2x21))"""
        #Array to store answers.
        #Format is: k x (dP, d²P, χ²)
        kbins = np.array(kbins)
        npvals=np.size(s_knot.pvals)
        nk=21
        results=np.zeros(2*nk)
        pdifs=s_knot.pvals-s_knot.p0
        #This is to rescale by the mean flux, for generating mean flux tables.
        ###
        #tau_eff=0.0023*(1+redshift)**3.65
        #tmin=0.2*((1+redshift)/4.)**2
        #tmax=0.5*((1+redshift)/4.)**4
        #teffs=tmin+s_knot.pvals*(tmax-tmin)/30.
        #pdifs=teffs/tau_eff-1.
        ###
        ured=np.ceil(redshift*5)/5.
        lred=np.floor(redshift*5)/5.
        usnap=self.GetSnap(ured)
        lsnap=self.GetSnap(lred)
        #Load the data
        (k,uPFp0)=self.loadpk(s_knot.bstft+self.suf+usnap+self.ext,s_knot.bfbox)
        uPower=np.zeros((npvals,np.size(k)))
        for i in np.arange(0,np.size(s_knot.names)):
            (k,uPower[i,:])=self.loadpk(s_knot.names[i]+self.suf+usnap+self.ext, s_knot.bfbox)
        (k,lPFp0)=self.loadpk(s_knot.bstft+self.suf+lsnap+self.ext,s_knot.bfbox)
        lPower=np.zeros((npvals,np.size(k)))
        for i in np.arange(0,np.size(s_knot.names)):
            (k,lPower[i,:])=self.loadpk(s_knot.names[i]+self.suf+lsnap+self.ext, s_knot.bfbox)
        PowerFluxes=5*((redshift-lred)*uPower+(ured-redshift)*lPower)
        PFp0=5*((redshift-lred)*uPFp0+(ured-redshift)*lPFp0)
        #So now we have an array of data values. 
        #Pass each k value to flux_deriv in turn.       
        for k in np.arange(0,nk):
            #(dPF, d2PF,chi2)=self.flux_deriv(PowerFluxes[:,k]/PFp0[k], pdifs)
            (dPF, d2PF)=self.flux_deriv(PowerFluxes[:,k]/PFp0[k], pdifs)
            results[k]=d2PF
            results[nk+k]=dPF
        return results
    
    def Getkbins(self):
        """Get the kbins to interpolate onto"""
        return np.arange(0,20,1)+0.5
    
    def plot_z(self,Knot,redshift,title="",ylabel="",legend=True):
        """ Plot comparisons between a bunch of sims on one graph 
            plot_z(Redshift, Sims to use ( eg, A1.14). 
            Note this will clear current figures."""
        #Load best-fit
        (simk,BFPk)=self.loadpk(Knot.bstft+self.suf+self.pre+self.GetSnap(redshift)+self.ext,self.bfbox)
        #Setup figure plot.
        ind=wheref(self.Zz, redshift)
        plt.figure(ind[0][0])
        plt.clf()
        if title != '':
            plt.title(title+" at z="+str(redshift),)
        plt.ylabel(ylabel)
        plt.xlabel(r"$\mathcal{F}$")
        line=np.array([])
        legname=np.array([])
        for sim in Knot.names:
            #(k,Pk)=self.loadpk(sim+self.suf+self.pre+self.GetSnap(redshift)+self.ext,self.box)
            Pk=self.loadpk(sim+self.suf+self.pre+self.GetSnap(redshift)+self.ext,self.box)  
            line=np.append(line, plt.semilogy(simk,Pk[1]/BFPk,linestyle="-", linewidth=1.5))
            legname=np.append(legname,sim)  
        plt.legend(line,legname)
        return
    
    def GetFlat(self,direc,si=0.0):
        """Get a power spectrum in the flat format we use
           for inputting some cosmomc tables"""
        #Pk_sdss=np.empty([11, 12])
        #For z=2.07 we need to average snap_011 and snap_010
        z=2.07
        PF_a=self.loadpk(direc+self.suf+"snapshot_011"+self.ext, self.box)
        PF_b=self.loadpk(direc+self.suf+"snapshot_010"+self.ext, self.box)
        PF1=(z-2.0)*5*(PF_b[1]-PF_a[1])+PF_a[1]
        z=2.52
        PF_a=self.loadpk(direc+self.suf+"snapshot_009"+self.ext, self.box)
        PF_b=self.loadpk(direc+self.suf+"snapshot_008"+self.ext, self.box)
        PF2=(z-2.4)*5*(PF_b[1]-PF_a[1])+PF_a[1]
        z=2.94
        PF_a=self.loadpk(direc+self.suf+"snapshot_007"+self.ext, self.box)
        PF_b=self.loadpk(direc+self.suf+"snapshot_006"+self.ext, self.box)
        PF3=(z-2.8)*5*(PF_b[1]-PF_a[1])+PF_a[1]
        PDF = np.array([PF1,PF2,PF3])
        #np.savetxt(sys.stdout,PDF.T("%1.8f","%1.8f","%1.8f"))
        np.savetxt(sys.stdout,PDF, fmt=("%1.8f","%1.8f","%1.8f"))
        return (PF1, PF2, PF3)


class knot:
    """A basic structure class to store a number of simulation runs, with parameter values."""
    names=()
    pvals=np.array([])
    p0=0.0
    qvals=np.array([])
    q0=0.0
    bstft=""
    bfbox=60.0
    def __init__(self, sims, pvals, p0, bstft,bfbox,qvals=np.array([]),q0=0):
        self.names=sims
        self.pvals=np.array(pvals)
        self.p0=p0
        self.qvals=np.array(qvals)
        self.q0=q0
        self.bstft=bstft
        self.bfbox=bfbox
        if np.size(sims) != np.size(pvals) and np.size(self.pvals[:,0]) != np.size(sims):
            raise DataError(str(np.size(pvals))+" pvals given, but "+str(np.size(sims))+" sims.")

    def GetPval(self,name):
        """ Get pval associated with a simulation name """
        ind=np.where(self.names == name)
        if np.size(ind):
            return self.pvals[ind]
        else:
            raise DataError(str(name)+" does not exist!") 
    
    def GetSnap(self, pval):
        """ Get name associated with a pval """
        ind=wheref(self.pvals,pval)
        if np.size(ind):
            return str(np.asarray(self.names)[ind][0])
        else:
            raise DataError("No snapshot with p="+str(pval))

class flux_interp:
    """A class to store the calculated flux derivatives"""
    #Derivs is stored in: params x redshifts x kbins x [dP, d2P, x2]
    derivs=np.array([])
    p0=np.array([])
    q0=np.array([])
    Zz=np.array([])
    kbins=np.array([])
    """Initialization done from flux_pow class lets us keep all the messy I/O in there."""
    def __init__(self,flux, Knots):
        if np.shape(Knots) == ():
            Knots=(Knots,)
        Knots=np.array(Knots)
        self.kbins=flux.Getkbins()
        tmp=np.fliplr(flux.calc_all(Knots[0],self.kbins))
        self.derivs=np.empty(np.shape(Knots)+np.shape(tmp))
        self.derivs[0]=tmp
        if np.size(Knots[0].p0) > 1:
            self.p0=np.empty([np.size(Knots),np.size(Knots[0].p0)])
            self.p0[0,:]=np.array(Knots[0].p0)
            self.q0=np.empty([np.size(Knots),np.size(Knots[0].q0)])
            self.q0[0,:]=np.array(Knots[0].q0)
            for i in np.arange(1,np.size(Knots)):
                self.derivs[i]=np.fliplr(flux.calc_all(Knots[i],self.kbins))
                self.p0[i,:]=np.array(Knots[i].p0)
                self.q0[i,:]=np.array(Knots[i].q0)
        else:
            self.p0=np.empty(np.shape(Knots))
            self.p0[0]=np.array(Knots[0].p0)
            for i in np.arange(1,np.size(Knots)):
                self.derivs[i]=np.fliplr(flux.calc_all(Knots[i],self.kbins))
                self.p0[i]=np.array(Knots[i].p0)

        self.Zz=np.flipud(flux.Zz)
    
    def GetPFSingleKnot(self, i, redshift, param,qaram=np.array([])):
        """ Get an interpolated estimate for the power spectrum with the change of a 
            single knot at a single redshift"""
        ind=wheref(self.Zz, redshift)
        kbins=np.size(self.kbins)
        if np.size(self.p0[i]) > 1:
            dp=param[ind]-self.p0[i,ind][0]
            if np.size(self.q0) > 0 and np.size(self.q0[i]) > 1:
                dq=qaram[ind]-self.q0[i,ind][0]
                total= self.derivs[i,0:kbins,ind]*dp**2+self.derivs[i,kbins:2*kbins,ind]*dp +  self.derivs[i,2*kbins:3*kbins,ind]*dq**2+self.derivs[i,3*kbins:4*kbins,ind]*dq
              #      +  self.derivs[i,4*kbins:,ind]*dq*dp
                return total
        else:
            dp=param-self.p0[i]
        return self.derivs[i,0:kbins,ind]*dp**2+self.derivs[i,kbins:,ind]*dp
    
    def GetPF(self, prms, redshift,qrms=np.empty([])):
        """Get an interpolated power spectrum estimate at a single redshift"""
        nbins=np.size(self.kbins)
        curve=np.zeros(nbins)
        maxi=np.shape(prms)[0]
        for i in np.arange(0,maxi):
            if np.size(qrms) >= maxi:
                curve=curve+self.GetPFSingleKnot(i, redshift,prms[i],qrms[i])
            else:
                curve=curve+self.GetPFSingleKnot(i, redshift,prms[i])
        return curve

    def Get_MV_Tables(self,j,flux):
        """Get tables in the format Matteo uses for CosmoMC"""
        ind = np.where(self.Zz >= 2.2)
        Zz=self.Zz[ind]
        nz=np.size(Zz)
        nk=np.size(self.kbins)
        # ???
        tmp=self.derivs[j,0:,ind][0].T
        nco=np.shape(self.derivs)[1]/nk
        nsk=np.size(flux.GetSDSSkbins(Zz[0]))
        deriv_r=np.zeros([nco*nsk,nz])
        for q in np.arange(nco):
            for i in np.arange(0,nz):
                deriv_r[q*nsk:(q+1)*nsk,i]=rebin(tmp[q*nk:(q+1)*nk,i],self.kbins,flux.GetSDSSkbins(Zz[i]))
        return deriv_r

    def Get_PDF_Tables(self, pdf,s_knot):
        """Get the pdf tables"""
        #Flux pdf has 3 redshift bins, 20 k bins.
        nk=21
        nz=3
        #Redshift bins are at 2.07, 2.52 and 2.94
        pz=np.array([2.07,2.52,2.94])
        fd=np.zeros([2*nk, nz])
        #Call flux_deriv_const_z for each redshift
        #This gets them in increasing redshift.
        for i in np.arange(0,nz):
            fd[:,i]=pdf.calc_z(pz[i], s_knot)
        return fd
           
class matteo_flux_interp(flux_interp):
    """Load pre-calculated tables in the style Matteo uses"""
    def __init__(self, file, p0):
        #The format is: rows are k bins, columns are redshift bins.
        #First 12x11 rows are the second order coeffs, second are the first order coeffs.
        data=np.loadtxt(file)
        self.derivs=np.zeros((1,24,11))
        self.derivs[0]=data
        self.Zz=np.flipud(np.array([4.2,4.0,3.8,3.6,3.4,3.2,3.0,2.8,2.6,2.4,2.2]))
        self.p0=np.array([p0])
        self.kbins=np.array([0.00141,0.00178,0.00224,0.00282,0.00355,0.00447,0.00562,0.00708,0.00891,0.01122,0.01413,0.01778])
        flux_interp.__init__(self, file, p0)
    
    def dpf(self,z,p):
        """Easier wrapper"""
        return self.GetPFSingleKnot(0,z,p)

    def tpf(self, z,t):
        """Use this function if the variable in question is tau"""
#        tbf = np.array([0.896000,0.756733,0.657800,0.600400,0.513000,0.42900,0.379867,0.3285330,0.2714000,0.2192,0.178000])
        tbf = 0.0023*(1+self.Zz)**3.65

        ind=wheref(self.Zz, z)
        return (t/tbf[ind]-1)*(self.derivs[0][ind, :,0])+(self.derivs[0][ind,:,1])*(t/tbf[ind]-1)**2

if __name__=='__main__':
    flux=flux_pow()
    matter=matter_pow()
    fpdf=flux_pdf()
    A_knot=knot(("A0.54/","A0.74/","A0.84/","A1.04/", "A1.14/","A1.34/"), (0.54,0.74,0.84,1.04,1.14,1.34),0.94,"best-fit/", 60)
    AA_knot=knot(("AA0.54/","AA0.74/","AA1.14/","AA1.34/"), (0.54,0.74,1.14,1.34),0.94,"boxcorr400/", 120)
    B_knot=knot(("B0.33/","B0.53/","B0.73/", "B0.83/", "B1.03/","B1.13/", "B1.33/"), (0.33,0.53,0.73,0.83,1.03, 1.13,1.33),0.93,"best-fit/", 60)
    C_knot=knot(("C0.11/", "C0.31/","C0.51/","C0.71/","C1.11/","C1.31/","C1.51/"),(0.11, 0.31,0.51,0.71, 1.11,1.31,1.51),0.91,"bf2/", 60)
    D_knot=knot(("D0.50/","D0.70/","D1.10/","D1.20/", "D1.30/", "D1.50/", "D1.70/"),(0.50, 0.70,1.10,1.20,1.30, 1.50, 1.70),0.90,"bfD/", 48)
    interp=flux_interp(flux, (AA_knot, B_knot, C_knot, D_knot))
#Thermal parameters for models

#Models where gamma is varied
    bf2zg=np.array([1.5704182,1.5754168,1.5797292,1.5836439,1.5870027,1.5915027,1.5943816,1.5986097,1.6027860,1.6073484,1.6116327,1.6158375])
    bf2zt=np.array([21221.521,21915.172,22303.908,22432.774,22889.881,22631.245,22610.916,22458.702,22020.437,21752.465,21278.358,20720.927])/1e3
    bf2g=np.array([1.4260277,1.4332204,1.4354097,1.4422902,1.4455976,1.4502961,1.4547729,1.4593188,1.4637958,1.4682989,1.4728728,1.4769461 ])
    bf2t=np.array([21453.313,21917.668,22655.974, 22600.650, 23061.612, 22798.62,22694.608,22721.762,22208.044, 21826.779, 21552.183,20908.159])/1e3
    bf2bg=np.array([1.1853212,1.1950833,1.2041183,1.2128127,1.2183342,1.2275667,1.2328254,1.2391863,1.2463307,1.2518918,1.2576843,1.263106])
    bf2bt=np.array([21464.978,22181.427,22594.685,22749.661,23218.541,22985.179,22974.422,22822.704,22387.685,22101.844,21612.527,21031.671])/1e3
    bf2cg=np.array([1.0216708,1.0334782,1.0445199,1.0552473,1.0616736,1.0729254,1.0792092,1.0865544,1.0950485,1.1010989,1.1077290,1.1138842])
    bf2ct=np.array([21561.621,22289.611,22714.780,22882.540,23358.805,23138.204,23134.987,22988.727,22560.401,22273.657,21786.965,21207.151])/1e3
    bf2dg=np.array([0.69947395,0.71491958,0.72959149,0.74404393,0.75198024,0.76702529,0.77516276,0.78435663,0.79540249,0.80256333,0.81069041,0.81829536])
    bf2dt=np.array([21769.984,22520.422,22969.096,23161.952,23655.146,23460.672,23475.417,23345.052,22934.061,22657.571,22182.125,21612.365])/1e3
        
#Models where T0 is varied; gamma changes a bit also
    T15g=np.array([1.3485881,1.3577712,1.3659720,1.3736938,1.3795726,1.3878026,1.3931488,1.3998762,1.4070048,1.4137031,1.4203951,1.4270162])
    T15t=np.array([13985.271,14489.076,14788.379,14914.136,15257.258,15123.863,15145.278,15078.820,14821.798,14677.305,14395.929,14059.430])/1e3
    T35g=np.array([1.3398174,1.3480600,1.3555022,1.3624323,1.3671665,1.3741617,1.3781567,1.3829295,1.3879474,1.3919720,1.3960214,1.3998402])
    T35t=np.array([32144.682,33160.696,33728.095,33910.458,34564.844,34159.548,34094.253,33809.077,33095.110,32603.121,31807.908,30881.237])/1e3
    T45g=np.array([1.3248931,1.3350548,1.3440339,1.3521382,1.3579792,1.3654530,1.3699611,1.3748911,1.3798712,1.3838409,1.3877698,1.3915019])
    T45t=np.array([40273.406,41586.734,42333.225,42588.319,43436.152,42930.669,42854.484,42486.193,41569.709,40929.328,39905.296,38717.452])/1e3

#Check knot
    bf2ag=np.array([1.0184905 ,1.0332849 ,1.0404092 ,1.0538235 ,1.0598905 ,1.0695964 ,1.0771414 ,1.0827464 ,1.0904784 ,1.0964669 ,1.1009428,1.1068357])
    bf2at=np.array([26914.856, 27497.555, 28407.030, 28357.785, 28919.376, 28610.038, 28478.749, 28484.856, 27841.160, 27335.328, 26933.453,26099.643])/1e3

    G_knot=knot(("bf2z/","bf2b/","bf2c/","bf2d/", "bf2T15/","bf2T35/","bf2T45/","bf2a/"),(bf2zg,bf2bg,bf2cg,bf2dg,T15g,T35g,T45g,bf2ag),bf2g,"bf2/",60, (bf2zt,bf2bt,bf2ct,bf2dt,T15t,T35t,T45t,bf2at),bf2t)
    g_int=flux_interp(flux,(G_knot))
