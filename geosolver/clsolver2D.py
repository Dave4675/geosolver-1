"""A generic 2D geometric constraint solver.

The solver finds a generic solution
for problems formulated by Clusters. The generic solution 
is a directed acyclic graph of Clusters and Methods. Particilar problems
and solutions are represented by a Configuration for each cluster.
"""
# import sys

# if sys.version_info[0] > 2:
#     py2 = False
# else:
#     py2 = True
#
# if py2 is True:
#     from sets import Set, ImmutableSet
# else:
#     pass

from geosolver.clsolver import *
from geosolver.multimethod import MultiMethod
from geosolver.diagnostic import diag_print
from geosolver.selconstr import NotCounterClockwiseConstraint, \
    NotClockwiseConstraint, NotAcuteConstraint, NotObtuseConstraint
from geosolver.intersections import *
from geosolver.configuration import Configuration
from geosolver.cluster import *


class Merge(ClusterMethod):
    """A derive is a method such that a single ouput cluster is a 
    subconsraint of a single input cluster."""

    def __init__(self):
        ClusterMethod.__init__(self)



class Derive(ClusterMethod):
    """A merge is a method such that a single ouput cluster satisfies
    all constraints in several input clusters. The output cluster
    replaces the input clusters in the constriant problem"""

    def __init__(self):
        ClusterMethod.__init__(self)



class ClusterSolver2D(ClusterSolver):
    """A generic 2D geometric constraint solver. 
    
    Finds a geneneric solution for problems formulated by cluster-constraints.

    Constraints are Clusers: Rigids, Hedgehogs and Balloons. 
    Cluster are added and removed using the add and remove methods. 
    After adding each Cluster, the solver tries to merge it with
    other clusters, resulting in new Clusters and Methods.

    For each Cluster a set of Configurations can be set using the
    set method. Configurations are propagated via Methods and can
    be retrieved with the get method. 
    """

    # ------- PUBLIC METHODS --------

    def __init__(self):
        """Instantiate a ClusterSolver2D"""
        ClusterSolver.__init__(self, dimension=2)

    # ------------ INTERNALLY USED METHODS --------

    # --------------
    # search methods
    # --------------

    def _search(self, newcluster):
        if isinstance(newcluster, Rigid):
            self._search_from_rigid(newcluster)
        elif isinstance(newcluster, Hedgehog):
            self._search_from_hog(newcluster)
        elif isinstance(newcluster, Balloon):
            self._search_from_balloon(newcluster)
        else:
            raise Exception("don't know how to search from "+str(newcluster))
    # end _search

    def _search_from_balloon(self, balloon):
        if self._search_absorb_from_balloon(balloon):
            return
        if self._search_balloon_from_balloon(balloon):
            return
        if self._search_cluster_from_balloon(balloon):
            return
        self._search_hogs_from_balloon(balloon)
    #end def _search_from_baloon

    def _search_from_hog(self, hog):
        if self._search_absorb_from_hog(hog):
            return
        if self._search_merge_from_hog(hog):
            return
        if self._search_balloon_from_hog(hog):
            return
        self._search_hogs_from_hog(hog)
    #end def _search_from_hog

    def _search_from_rigid(self, cluster):
        if self._search_absorb_from_cluster(cluster):
            return
        if self._search_balloonclustermerge_from_cluster(cluster):
            return
        if self._search_merge_from_cluster(cluster):
            return
        self._search_hogs_from_cluster(cluster)
    # end def _search_from_cluster

    # ------ Absorb hogs -------

    def _search_absorb_from_balloon(self, balloon):
        for cvar in balloon.vars:
            # find all incident hogs
            hogs = self._find_hogs(cvar)
            # determine shared vertices per hog
            for hog in hogs:
                shared = Set(hog.xvars).intersection(balloon.vars)
                if len(shared) == len(hog.xvars):
                    return self._merge_balloon_hog(balloon, hog)

    def _search_absorb_from_cluster(self, cluster):
        for cvar in cluster.vars:
            # find all incident hogs
            hogs = self._find_hogs(cvar)
            # determine shared vertices per hog
            for hog in hogs:
                shared = Set(hog.xvars).intersection(cluster.vars)
                if len(shared) == len(hog.xvars):
                    return self._merge_cluster_hog(cluster, hog)

    def _search_absorb_from_hog(self, hog):
        dep = self.find_dependend(hog.cvar)
        # case BH (overconstrained):
        balloons = filter(lambda x: isinstance(x,Balloon) and self.is_top_level(x), dep)
        sharecx = filter(lambda x: len(Set(hog.xvars).intersection(x.vars)) >=1, balloons)
        for balloon in sharecx:
            sharedcx = Set(balloon.vars).intersection(hog.xvars)
            if len(sharedcx) == len(hog.xvars):
                return self._merge_balloon_hog(balloon, hog)
        # case CH (overconstrained)
        clusters = filter(lambda x: isinstance(x,Rigid) and self.is_top_level(x), dep)
        sharecx = filter(lambda x: len(Set(hog.xvars).intersection(x.vars)) >=1, clusters)
        for cluster in sharecx:
            sharedcx = Set(cluster.vars).intersection(hog.xvars)
            if len(sharedcx) == len(hog.xvars):
                return self._merge_cluster_hog(cluster, hog)

    # ------- DEALING WITH BALLOONS  ---------

    def _find_balloons(self, variables):
        balloons = Set()
        for var in variables:
            deps = self.find_dependend(var)
            balls = filter(lambda x: isinstance(x,Balloon), deps)
            balloons = balloons.intersection(balls)
        return balloons

    def _make_balloon(self, var1, var2, var3, hog1, hog2):
        diag_print("_make_balloon "+str(var1)+","+str(var2)+","+str(var3),"clsolver")
        # derive sub-hogs if nessecairy
        vars = Set([var1, var2, var3])
        subvars1 = vars.intersection(hog1.xvars)
        if len(hog1.xvars) > 2:
            hog1 = self._derive_subhog(hog1, subvars1)
        subvars2 = vars.intersection(hog2.xvars)
        if len(hog2.xvars) > 2:
            hog2 = self._derive_subhog(hog2, subvars2)
        # create balloon and method
        balloon = Balloon([var1, var2, var3])
        balloonmethod = BalloonFromHogs(hog1, hog2, balloon)
        self._add_merge(balloonmethod)
        return balloon

    def _search_balloon_from_hog(self,hog):
        newballoons = []
        var1 = hog.cvar
        for var2 in hog.xvars:
            hogs = self._find_hogs(var2)
            for hog2 in hogs:
                if var1 in hog2.xvars:
                    for var3 in hog2.xvars:
                        if var3 != var2 and var3 in hog.xvars:
                            if not self._known_angle(var1, var3, var2):
                                newballoons.append(self._make_balloon(var1, var2, var3, hog, hog2))
        if len(newballoons) > 0:
            return newballoons
        else:
            return None

    def _search_balloon_from_balloon(self, balloon):
        map = {}    # map from adjacent balloons to variables shared with input balloon
        for var in balloon.vars:
            deps = self.find_dependend(var)
            balloons = filter(lambda x: isinstance(x,Balloon), deps)
            balloons = filter(lambda x: self.is_top_level(x), balloons)
            for bal2 in balloons:
                if bal2 != balloon:
                    if bal2 in map:
                        map[bal2].union_update([var])
                    else:
                        map[bal2] = Set([var])
        for bal2 in map:
            nvars = len(map[bal2])
            if nvars >= 2:
                return self._merge_balloons(balloon, bal2)
        return None

    def _search_cluster_from_balloon(self, balloon):
        diag_print("_search_cluster_from_balloon", "clsolver")
        map = {}    # map from adjacent clusters to variables shared with input balloon
        for var in balloon.vars:
            deps = self.find_dependend(var)
            clusters = filter(lambda x: isinstance(x,Rigid) or isinstance(x,Distance), deps)
            clusters = filter(lambda x: self.is_top_level(x), clusters)
            for c in clusters:
                if c in map:
                    map[c].union_update([var])
                else:
                    map[c] = Set([var])
        for cluster in map:
            nvars = len(map[cluster])
            if nvars >= 2:
                return self._merge_balloon_cluster(balloon, cluster)
        return None

    def _search_balloonclustermerge_from_cluster(self, rigid):
        diag_print("_search_balloonclustermerge_from_cluster", "clsolver")
        map = {}    # map from adjacent clusters to variables shared with input balloon
        for var in rigid.vars:
            deps = self.find_dependend(var)
            balloons = filter(lambda x: isinstance(x,Balloon), deps)
            balloons = filter(lambda x: self.is_top_level(x), balloons)
            for b in balloons:
                if b in map:
                    map[b].union_update([var])
                else:
                    map[b] = Set([var])
        for balloon in map:
            nvars = len(map[balloon])
            if nvars >= 2:
                return self._merge_balloon_cluster(balloon, rigid)
        return None

    def _merge_balloons(self, bal1, bal2):
        # create new balloon and merge method
        vars = Set(bal1.vars).union(bal2.vars)
        newballoon = Balloon(vars)
        merge = BalloonMerge(bal1,bal2,newballoon)
        self._add_merge(merge)
        return newballoon

    def _merge_balloon_cluster(self, balloon, cluster):
        # create new cluster and method
        vars = Set(balloon.vars).union(cluster.vars)
        newcluster = Rigid(list(vars))
        merge = BalloonRigidMerge(balloon,cluster,newcluster)
        self._add_merge(merge)
        return newcluster


    # ------- DEALING WITH HEDEGHOGS ---------

    def _find_hogs(self, cvar):
        deps = self.find_dependend(cvar)
        hogs = filter(lambda x: isinstance(x,Hedgehog), deps)
        hogs = filter(lambda x: x.cvar == cvar, hogs)
        hogs = filter(lambda x: self.is_top_level(x), hogs)
        return hogs

    def _make_hog_from_cluster(self, cvar, cluster):
        xvars = Set(cluster.vars)
        xvars.remove(cvar)
        hog = Hedgehog(cvar,xvars)
        self._add_hog(hog)
        method = Rigid2Hog(cluster, hog)
        self._add_method(method)
        return hog

    def _make_hog_from_balloon(self, cvar, balloon):
        xvars = Set(balloon.vars)
        xvars.remove(cvar)
        hog = Hedgehog(cvar,xvars)
        self._add_hog(hog)
        method = Balloon2Hog(balloon, hog)
        self._add_method(method)
        return hog

    def _search_hogs_from_balloon(self, newballoon):
        #diag_print("_search_hogs_from_balloon "+str(newballoon),"clsolver")
        if self.dimension != 2:
            return None
        if len(newballoon.vars) <= 2:
            return None
        # create/merge hogs
        for cvar in newballoon.vars:
            # potential new hog
            xvars = Set(newballoon.vars)
            xvars.remove(cvar)
            # find all incident hogs
            hogs = self._find_hogs(cvar)
            # determine shared vertices per hog
            for hog in hogs:
                shared = Set(hog.xvars).intersection(xvars)
                if len(shared) >= 1 and len(shared) < len(hog.xvars) and len(shared) < len(xvars):
                    tmphog = Hedgehog(cvar, xvars)
                    if not self._graph.has_vertex(tmphog):
                        newhog = self._make_hog_from_balloon(cvar,newballoon)
                        self._merge_hogs(hog, newhog)
            #end for
        #end for

    def _search_hogs_from_cluster(self, newcluster):
        #diag_print("_search_hogs_from_cluster "+str(newcluster),"clsolver")
        if self.dimension != 2:
            return None
        if len(newcluster.vars) <= 2:
            return None
        # create/merge hogs
        for cvar in newcluster.vars:
            # potential new hog
            xvars = Set(newcluster.vars)
            xvars.remove(cvar)
            # find all incident hogs
            hogs = self._find_hogs(cvar)
            # determine shared vertices per hog
            for hog in hogs:
                shared = Set(hog.xvars).intersection(xvars)
                if len(shared) >= 1 and len(shared) < len(hog.xvars) and len(shared) < len(xvars):
                    tmphog = Hedgehog(cvar, xvars)
                    if not self._graph.has_vertex(tmphog):
                        newhog = self._make_hog_from_cluster(cvar,newcluster)
                        self._merge_hogs(hog, newhog)
            #end for
        #end for

    def _search_hogs_from_hog(self, newhog):
        #diag_print("_search_hogs_from_hog "+str(newhog),"newhog")
        if self.dimension != 2:
            return None
        # find adjacent clusters
        dep = self.find_dependend(newhog.cvar)
        top = filter(lambda c: self.is_top_level(c), dep)
        clusters = filter(lambda x: isinstance(x,Rigid), top)
        balloons = filter(lambda x: isinstance(x,Balloon), top)
        hogs = self._find_hogs(newhog.cvar)
        tomerge = []
        for cluster in clusters:
            if len(cluster.vars) < 3:
                continue
            # determine shared vars
            xvars = Set(cluster.vars)
            xvars.remove(newhog.cvar)
            shared = Set(newhog.xvars).intersection(xvars)
            if len(shared) >= 1 and len(shared) < len(xvars) and len(shared) < len(newhog.xvars):
                tmphog = Hedgehog(newhog.cvar, xvars)
                if not self._graph.has_vertex(tmphog):
                    newnewhog = self._make_hog_from_cluster(newhog.cvar, cluster)
                    tomerge.append(newnewhog)
        for balloon in balloons:
            # determine shared vars
            xvars = Set(balloon.vars)
            xvars.remove(newhog.cvar)
            shared = Set(newhog.xvars).intersection(xvars)
            if len(shared) >= 1 and len(shared) < len(xvars) and len(shared) < len(newhog.xvars):
                tmphog = Hedgehog(newhog.cvar, xvars)
                if not self._graph.has_vertex(tmphog):
                    newnewhog = self._make_hog_from_balloon(newhog.cvar, balloon)
                    tomerge.append(newnewhog)
        for hog in hogs:
            if hog == newhog:
                continue
            # determine shared vars
            shared = Set(newhog.xvars).intersection(hog.xvars)
            if len(shared) >= 1 and len(shared) < len(hog.xvars) and len(shared) < len(newhog.xvars):
                # if mergeable, then create new hog
                tomerge.append(hog)

        if len(tomerge) == 0:
            return None
        else:
            lasthog = newhog
            for hog in tomerge:
                lasthog = self._merge_hogs(lasthog, hog)
            return lasthog

    # end def

    def _merge_hogs(self, hog1, hog2):
        diag_print("merging "+str(hog1)+"+"+str(hog2), "clsolver")
        # create new hog and method
        xvars = Set(hog1.xvars).union(hog2.xvars)
        mergedhog = Hedgehog(hog1.cvar, xvars)
        method = MergeHogs(hog1, hog2, mergedhog)
        self._add_merge(method)
        return mergedhog

    # end def _merge_hogs

    # ------ DEALING WITH CLUSTER MERGES -------


    def _search_merge_from_hog(self, hog):

        # case CH (overconstrained)
        dep = self.find_dependend(hog.cvar)
        clusters = filter(lambda x: isinstance(x,Rigid) and self.is_top_level(x), dep)
        sharecx = filter(lambda x: len(Set(hog.xvars).intersection(x.vars)) >=1, clusters)
        for cluster in sharecx:
            sharedcx = Set(cluster.vars).intersection(hog.xvars)
            if len(sharedcx) == len(hog.xvars):
                return self._merge_cluster_hog(cluster, hog)

        # case CHC
        for i in range(len(sharecx)):
            c1 = sharecx[i]
            for j in range(i+1, len(sharecx)):
                c2 = sharecx[j]
                return self._merge_cluster_hog_cluster(c1, hog, c2)

        # case CCH
        sharex = Set()
        for var in hog.xvars:
            dep = self.find_dependend(var)
            sharex.union_update(filter(lambda x: isinstance(x,Rigid) and self.is_top_level(x), dep))
        for c1 in sharecx:
            for c2 in sharex:
                if c1 == c2: continue
                shared12 = Set(c1.vars).intersection(c2.vars)
                sharedh2 = Set(hog.xvars).intersection(c2.vars)
                shared2 = shared12.union(sharedh2)
                if len(shared12) >= 1 and len(sharedh2) >= 1 and len(shared2) == 2:
                    return self._merge_cluster_cluster_hog(c1, c2, hog)
        return None


    def _search_merge_from_cluster(self, newcluster):
        diag_print ("_search_merge "+str(newcluster), "clsolver")
        # find clusters overlapping with new cluster
        overlap = {}
        for var in newcluster.vars:
            # get dependent objects
            dep = self._graph.outgoing_vertices(var)
            # only clusters
            dep = filter(lambda c: self._graph.has_edge("_rigids",c), dep)
            # only top level
            dep = filter(lambda c: self.is_top_level(c), dep)
            # remove newcluster
            if newcluster in dep:
                dep.remove(newcluster)
            for cluster in dep:
                if cluster in overlap:
                    overlap[cluster].append(var)
                else:
                    overlap[cluster] = [var]

        # point-cluster merge
        for cluster in overlap:
            if len(overlap[cluster]) == 1:
                if len(cluster.vars) == 1:
                    return self._merge_point_cluster(cluster, newcluster)
                elif len(newcluster.vars) == 1:
                    return self._merge_point_cluster(newcluster, cluster)

        # two cluster merge (overconstrained)
        for cluster in overlap:
            if len(overlap[cluster]) >= self.dimension:
                return self._merge_cluster_pair(cluster, newcluster)

        # three cluster merge
        clusterlist = overlap.keys()
        for i in range(len(clusterlist)):
            c1 = clusterlist[i]
            for j in range(i+1, len(clusterlist)):
                c2 = clusterlist[j]
                shared12 = Set(c1.vars).intersection(c2.vars)
                shared13 = Set(c1.vars).intersection(newcluster.vars)
                shared23 = Set(c2.vars).intersection(newcluster.vars)
                shared1 = shared12.union(shared13)
                shared2 = shared12.union(shared23)
                shared3 = shared13.union(shared23)
                if len(shared1) == self.dimension and\
                   len(shared1) == self.dimension and\
                   len(shared2) == self.dimension:
                    return self._merge_cluster_triple(c1, c2, newcluster)

        # merge with an angle, case 1
        for cluster in overlap:
            ovars = overlap[cluster]
            if len(ovars) == 1:
                cvar = ovars[0]
            else:
                raise Exception("unexpected case")
            hogs = self._find_hogs(cvar)
            for hog in hogs:
                sharedch = Set(cluster.vars).intersection(hog.xvars)
                sharednh = Set(newcluster.vars).intersection(hog.xvars)
                sharedh = sharedch.union(sharednh)
                if len(sharedch) >= 1 and len(sharednh) >= 1 and len(sharedh) >= 2:
                    return self._merge_cluster_hog_cluster(cluster, hog, newcluster)

        # merge with an angle, case 2
        #print "case c2"
        for var in newcluster.vars:
            hogs = self._find_hogs(var)
            for hog in hogs:
                sharednh = Set(newcluster.vars).intersection(hog.xvars)
                if len(sharednh) < 1:
                    continue
                for cluster in overlap:
                    sharednc = Set(newcluster.vars).intersection(cluster.vars)
                    if len(sharednc) != 1:
                        raise Exception("unexpected case")
                    if hog.cvar in cluster.vars:
                        #raise StandardError, "unexpected case"
                        continue
                    sharedch = Set(cluster.vars).intersection(hog.xvars)
                    sharedc = sharedch.union(sharednc)
                    if len(sharedch) >= 1 and len(sharedc) >= 2:
                        return self._merge_cluster_cluster_hog(newcluster, cluster, hog)
        #print "end case 2"

        # merge with an angle, case 3
        #print "case c3"
        for cluster in overlap:
            sharednc = Set(newcluster.vars).intersection(cluster.vars)
            if len(sharednc) != 1:
                raise Exception("unexpected case")
            for var in cluster.vars:
                hogs = self._find_hogs(var)
                for hog in hogs:
                    if hog.cvar in newcluster.vars:
                        # raise StandardError, "unexpected case"
                        continue
                    sharedhc = Set(newcluster.vars).intersection(hog.xvars)
                    sharedhn = Set(cluster.vars).intersection(hog.xvars)
                    sharedh = sharedhn.union(sharedhc)
                    sharedc = sharedhc.union(sharednc)
                    if len(sharedhc) >= 1 and len(sharedhn) >= 1 and len(sharedh) >= 2 and len(sharedc) == 2:
                        return self._merge_cluster_cluster_hog(cluster, newcluster, hog)
        #print "end case 3"
    # end def _search_merge

    def _merge_point_cluster(self, pointc, cluster):
        diag_print("_merge_point_cluster "+str(pointc)+","+str(cluster),"clsolver")
        #create new cluster and method
        allvars = Set(pointc.vars).union(cluster.vars)
        newcluster = Rigid(allvars)
        merge = Merge1C(pointc,cluster,newcluster)
        self._add_merge(merge)
        return newcluster
    #def

    def _merge_cluster_pair(self, c1, c2):
        """Merge a pair of clusters, structurally overconstrained.
           Rigid which contains root is used as origin.
           Returns resulting cluster. 
        """
        diag_print("_merge_cluster_pair "+str(c1)+","+str(c2),"clsolver")
        # always use root cluster as first cluster, swap if needed
        if not self._contains_root(c1) and not self._contains_root(c2):
            #raise "StandardError", "no root cluster"
            pass
        elif self._contains_root(c1) and self._contains_root(c2):
            raise Exception("two root clusters")
        elif self._contains_root(c2):
            diag_print("swap cluster order","clsolver")
            return self._merge_cluster_pair(c2, c1)
        #create new cluster and merge
        allvars = Set(c1.vars).union(c2.vars)
        newcluster = Rigid(allvars)
        merge = Merge2C(c1,c2,newcluster)
        self._add_merge(merge)
        return newcluster
    #def

    def _merge_cluster_hog(self, cluster, hog):
        """merge cluster and hog (absorb hog, overconstrained)"""
        diag_print("_merge_cluster_hog "+str(cluster)+","+str(hog),"clsolver")
        #create new cluster and merge
        newcluster = Rigid(cluster.vars)
        merge = MergeCH(cluster,hog, newcluster)
        self._add_merge(merge)
        return newcluster

    def _merge_balloon_hog(self, balloon, hog):
        """merge balloon and hog (absorb hog, overconstrained)"""
        diag_print("_merge_balloon_hog "+str(balloon)+","+str(hog),"clsolver")
        #create new balloon and merge
        newballoon = Balloon(balloon.vars)
        merge = MergeBH(balloon, hog, newballoon)
        self._add_merge(merge)
        return newballoon

    def _merge_cluster_triple(self, c1, c2, c3):
        """Merge a triple of clusters.
           Rigid which contains root is used as origin.
           Returns resulting cluster. 
        """
        diag_print("_merge_cluster_triple "+str(c1)+","+str(c2)+","+str(c3),"clsolver")
        # always use root cluster as first cluster, swap if needed
        if self._contains_root(c2):
            diag_print("swap cluster order","clsolver")
            return self._merge_cluster_triple(c2, c1, c3)
        elif self._contains_root(c3):
            diag_print("swap cluster order","clsolver")
            return self._merge_cluster_triple(c3, c1, c2)
        #create new cluster and method
        allvars = Set(c1.vars).union(c2.vars).union(c3.vars)
        newcluster = Rigid(allvars)
        merge = Merge3C(c1,c2,c3,newcluster)
        self._add_merge(merge)
        return newcluster
    #def

    def _merge_cluster_hog_cluster(self, c1, hog, c2):
        """merge c1 and c2 with a hog, with hog center in c1 and c2"""
        diag_print("_merge_cluster_hog_cluster "+str(c1)+","+str(hog)+","+str(c2),"clsolver")
        # always use root cluster as first cluster, swap if needed
        if self._contains_root(c2):
            diag_print("swap cluster order","clsolver")
            return self._merge_cluster_hog_cluster(c2, hog, c1)
        # derive sub-hog if nessecairy
        allvars = Set(c1.vars).union(c2.vars)
        xvars = Set(hog.xvars).intersection(allvars)
        if len(xvars) < len(hog.xvars):
            diag_print("deriving sub-hog","clsolver")
            hog = self._derive_subhog(hog, xvars)
        #create new cluster and merge
        allvars = Set(c1.vars).union(c2.vars)
        newcluster = Rigid(allvars)
        merge = MergeCHC(c1,hog,c2,newcluster)
        self._add_merge(merge)
        return newcluster

    def _derive_subhog(self, hog, xvars):
        subvars = Set(hog.xvars).intersection(xvars)
        assert len(subvars) == len(xvars)
        subhog = Hedgehog(hog.cvar, xvars)
        method = SubHog(hog, subhog)
        self._add_hog(subhog)
        self._add_method(method)
        return subhog

    def _merge_cluster_cluster_hog(self, c1, c2, hog):
        """merge c1 and c2 with a hog, with hog center only in c1"""
        diag_print("_merge_cluster_cluster_hog "+str(c1)+","+str(c2)+","+str(hog),"clsolver")
        # always use root cluster as first cluster, swap if needed
        if self._contains_root(c1) and self._contains_root(c2):
            raise StandardError("two root clusters!")
        elif not self._contains_root(c1) and not self._contains_root(c2):
            #raise StandardError, "no root cluster"
            pass
        elif self._contains_root(c2):
            return self._merge_cluster_cluster_hog(c2, c1, hog)
        # derive subhog if nessecairy
        allvars = Set(c1.vars).union(c2.vars)
        xvars = Set(hog.xvars).intersection(allvars)
        if len(xvars) < len(hog.xvars):
            diag_print("deriving sub-hog","clsolver")
            hog = self._derive_subhog(hog, xvars)
        # create new cluster and method
        newcluster = Rigid(allvars)
        merge = MergeCCH(c1,c2,hog,newcluster)
        self._add_merge(merge)
        return newcluster

# class ClusterSolver2D


# ---------- Methods for 2D solving -------------


class Merge1C(Merge):
    """Represents a merging of a one-point cluster with any other cluster 
       The first cluster determines the orientation of the resulting
       cluster
    """
    def __init__(self, in1, in2, out):
        self._inputs = [in1, in2]
        self._outputs = [out]
        self.overconstrained = False
        self.consistent = True
        MultiMethod.__init__(self)

    def __str__(self):
        s =  "merge1C("+str(self._inputs[0])+"+"+str(self._inputs[1])+"->"+str(self._outputs[0])+")"
        s += "[" + self.status_str()+"]"
        return s

    def multi_execute(self, inmap):
        diag_print("Merge1C.multi_execute called","clmethods")
        c1 = self._inputs[0]
        c2 = self._inputs[1]
        conf1 = inmap[c1]
        conf2 = inmap[c2]
        #res = conf1.merge2D(conf2)
        #return [res]
        if len(c1.vars) == 1:
            return [conf2.copy()]
        else:
            return [conf1.copy()]

class Merge2C(Merge):
    """Represents a merging of two clusters (overconstrained)
       The first cluster determines the orientation of the resulting
       cluster
    """
    def __init__(self, in1, in2, out):
        self.input1 = in1
        self.input2 = in2
        self.output = out
        self._inputs = [in1, in2]
        self._outputs = [out]
        self.overconstrained = True
        self.consistent = True
        MultiMethod.__init__(self)

    def __str__(self):
        s =  "merge2C("+str(self.input1)+"+"+str(self.input2)+"->"+str(self.output)+")"
        s += "[" + self.status_str()+"]"
        return s

    def multi_execute(self, inmap):
        diag_print("Merge2C.multi_execute called","clmethods")
        c1 = self._inputs[0]
        c2 = self._inputs[1]
        conf1 = inmap[c1]
        conf2 = inmap[c2]
        return [conf1.merge2D(conf2)]

class MergeCH(Merge):
    """Represents a merging of a cluster and a hog (where
       the hog is absorbed by the cluster). Overconstrained.
    """
    def __init__(self, cluster, hog, out):
        self.cluster = cluster
        self.hog = hog
        self.output = out
        self._inputs = [cluster, hog]
        self._outputs = [out]
        self.overconstrained = True
        self.consistent = True
        MultiMethod.__init__(self)

    def __str__(self):
        s =  "mergeCH("+str(self.cluster)+"+"+str(self.hog)+"->"+str(self.output)+")"
        s += "[" + self.status_str()+"]"
        return s

    def multi_execute(self, inmap):
        diag_print("MergeCH.multi_execute called","clmethods")
        conf1 = inmap[self.cluster]
        #conf2 = inmap[self.hog]
        return [conf1.copy()]

class MergeBH(Merge):
    """Represents a merging of a balloon and a hog (where
       the hog is absorbed by the balloon). Overconstrained.
    """
    def __init__(self, balloon, hog, out):
        self.balloon = balloon
        self.hog = hog
        self.output = out
        self._inputs = [balloon, hog]
        self._outputs = [out]
        self.overconstrained = True
        self.consistent = True
        MultiMethod.__init__(self)

    def __str__(self):
        s =  "mergeBH("+str(self.balloon)+"+"+str(self.hog)+"->"+str(self.output)+")"
        s += "[" + self.status_str()+"]"
        return s

    def multi_execute(self, inmap):
        diag_print("MergeBH.multi_execute called","clmethods")
        conf1 = inmap[self.balloon]
        #conf2 = inmap[self.hog]
        return [conf1.copy()]


class Merge3C(Merge):
    """Represents a merging of three clusters 
       The first cluster determines the orientation of the resulting
       cluster
    """
    def __init__(self, c1, c2, c3, out):
        self.input1 = c1
        self.input2 = c2
        self.input3 = c3
        self.output = out
        self._inputs = [c1, c2, c3]
        self._outputs = [out]
        self.overconstrained = False
        self.consistent = True
        MultiMethod.__init__(self)
        # check coincidence
        shared12 = Set(c1.vars).intersection(c2.vars)
        shared13 = Set(c1.vars).intersection(c3.vars)
        shared23 = Set(c2.vars).intersection(c3.vars)
        shared1 = shared12.union(shared13)
        shared2 = shared12.union(shared23)
        shared3 = shared13.union(shared23)
        if len(shared12) < 1:
            raise Exception("underconstrained c1 and c2")
        elif len(shared12) > 1:
            diag_print("overconstrained CCC - c1 and c2", "clmethods")
            self.overconstrained = True
        if len(shared13) < 1:
            raise Exception("underconstrained c1 and c3")
        elif len(shared13) > 1:
            diag_print("overconstrained CCC - c1 and c3", "clmethods")
            self.overconstrained = True
        if len(shared23) < 1:
            raise Exception("underconstrained c2 and c3")
        elif len(shared23) > 1:
            diag_print("overconstrained CCC - c2 and c3", "clmethods")
            self.overconstrained = True
        if len(shared1) < 2:
            raise Exception("underconstrained c1")
        elif len(shared1) > 2:
            diag_print("overconstrained CCC - c1", "clmethods")
            self.overconstrained = True
        if len(shared2) < 2:
            raise Exception("underconstrained c2")
        elif len(shared2) > 2:
            diag_print("overconstrained CCC - c2", "clmethods")
            self.overconstrained = True
        if len(shared3) < 2:
            raise Exception("underconstrained c3")
        elif len(shared3) > 2:
            diag_print("overconstrained CCC - c3", "clmethods")
            self.overconstrained = True

    def __str__(self):
        s = "merge3C("+str(self.input1)+"+"+str(self.input2)+"+"+str(self.input3)+"->"+str(self.output)+")"
        s += "[" + self.status_str()+"]"
        return s

    def multi_execute(self, inmap):
        diag_print("Merge3C.multi_execute called","clmethods")
        c1 = inmap[self._inputs[0]]
        c2 = inmap[self._inputs[1]]
        c3 = inmap[self._inputs[2]]
        shared12 = Set(c1.vars()).intersection(c2.vars()).difference(c3.vars())
        shared13 = Set(c1.vars()).intersection(c3.vars()).difference(c2.vars())
        shared23 = Set(c2.vars()).intersection(c3.vars()).difference(c1.vars())
        v1 = list(shared12)[0]
        v2 = list(shared13)[0]
        v3 = list(shared23)[0]
        assert v1 != v2
        assert v1 != v3
        assert v2 != v3
        p11 = c1.get(v1)
        p21 = c1.get(v2)
        d12 = vector.norm(p11-p21)
        p23 = c3.get(v2)
        p33 = c3.get(v3)
        d23 = vector.norm(p23-p33)
        p32 = c2.get(v3)
        p12 = c2.get(v1)
        d31 = vector.norm(p32-p12)
        ddds = solve_ddd(v1,v2,v3,d12,d23,d31)
        solutions = []
        for s in ddds:
            solution = c1.merge2D(s).merge2D(c2).merge2D(c3)
            solutions.append(solution)
        return solutions

    def prototype_constraints(self):
        c1 = self._inputs[0]
        c2 = self._inputs[1]
        c3 = self._inputs[2]
        shared12 = Set(c1.vars).intersection(c2.vars).difference(c3.vars)
        shared13 = Set(c1.vars).intersection(c3.vars).difference(c2.vars)
        shared23 = Set(c2.vars).intersection(c3.vars).difference(c1.vars)
        v1 = list(shared12)[0]
        v2 = list(shared13)[0]
        v3 = list(shared23)[0]
        assert v1 != v2
        assert v1 != v3
        assert v2 != v3
        constraints = []
        constraints.append(NotCounterClockwiseConstraint(v1,v2,v3))
        constraints.append(NotClockwiseConstraint(v1,v2,v3))
        return constraints

def solve_ddd(v1,v2,v3,d12,d23,d31):
    diag_print("solve_ddd: %s %s %s %f %f %f"%(v1,v2,v3,d12,d23,d31),"clmethods")
    p1 = vector.vector([0.0,0.0])
    p2 = vector.vector([d12,0.0])
    p3s = cc_int(p1,d31,p2,d23)
    solutions = []
    for p3 in p3s:
        solution = Configuration({v1:p1, v2:p2, v3:p3})
        solutions.append(solution)
    return solutions

class MergeCHC(Merge):
    """Represents a merging of two clusters and a hedgehog
       The first cluster determines the orientation of the resulting
       cluster
    """
    def __init__(self, c1, hog, c2, out):
        self.c1 = c1
        self.hog = hog
        self.c2 = c2
        self.output = out
        self._inputs = [c1, hog, c2]
        self._outputs = [out]
        self.overconstrained = False
        self.consistent = True
        MultiMethod.__init__(self)
        # check coincidence
        if not (hog.cvar in c1.vars and hog.cvar in c2.vars):
            raise Exception("hog.cvar not in c1.vars and c2.vars")
        shared12 = Set(c1.vars).intersection(c2.vars)
        shared1h = Set(c1.vars).intersection(hog.xvars)
        shared2h = Set(c2.vars).intersection(hog.xvars)
        shared1 = shared12.union(shared1h)
        shared2 = shared12.union(shared2h)
        sharedh = shared1h.union(shared2h)
        if len(shared12) < 1:
            raise Exception("underconstrained c1 and c2")
        elif len(shared12) > 1:
            diag_print("overconstrained CHC - c1 and c2", "clmethods")
            self.overconstrained = True
        if len(shared1h) < 1:
            raise Exception("underconstrained c1 and hog")
        elif len(shared1h) > 1:
            diag_print("overconstrained CHC - c1 and hog", "clmethods")
            self.overconstrained = True
        if len(shared2h) < 1:
            raise Exception("underconstrained c2 and hog")
        elif len(shared2h) > 1:
            diag_print("overconstrained CHC - c2 and hog", "clmethods")
            self.overconstrained = True
        if len(shared1) < 2:
            raise Exception("underconstrained c1")
        elif len(shared1) > 2:
            diag_print("overconstrained CHC - c1", "clmethods")
            self.overconstrained = True
        if len(shared2) < 2:
            raise Exception("underconstrained c2")
        elif len(shared2) > 2:
            diag_print("overconstrained CHC - c2", "clmethods")
            self.overconstrained = True
        if len(sharedh) < 2:
            raise Exception("underconstrained hog")
        elif len(shared1) > 2:
            diag_print("overconstrained CHC - hog", "clmethods")
            self.overconstrained = True

    def __str__(self):
        s = "mergeCHC("+str(self.c1)+"+"+str(self.hog)+"+"+str(self.c2)+"->"+str(self.output)+")"
        s += "[" + self.status_str()+"]"
        return s

    def multi_execute(self, inmap):
        diag_print("MergeCHC.multi_execute called","clmethods")
        # determine vars
        shared1 = Set(self.hog.xvars).intersection(self.c1.vars)
        shared2 = Set(self.hog.xvars).intersection(self.c2.vars)
        v1 = list(shared1)[0]
        v2 = self.hog.cvar
        v3 = list(shared2)[0]
        # get configs
        conf1 = inmap[self.c1]
        confh = inmap[self.hog]
        conf2 = inmap[self.c2]
        # determine angle
        p1h = confh.get(v1)
        p2h = confh.get(v2)
        p3h = confh.get(v3)
        a123 = angle_3p(p1h, p2h, p3h)
        # d1c
        p11 = conf1.get(v1)
        p21 = conf1.get(v2)
        d12 = distance_2p(p11,p21)
        # d2c
        p32 = conf2.get(v3)
        p22 = conf2.get(v2)
        d23 = distance_2p(p32,p22)
        # solve
        dads = solve_dad(v1,v2,v3,d12,a123,d23)
        solutions = []
        for s in dads:
            solution = conf1.merge2D(s).merge2D(conf2)
            solutions.append(solution)
        return solutions

def solve_dad(v1,v2,v3,d12,a123,d23):
    diag_print("solve_dad: %s %s %s %f %f %f"%(v1,v2,v3,d12,a123,d23),"clmethods")
    p2 = vector.vector([0.0, 0.0])
    p1 = vector.vector([d12, 0.0])
    p3s = [ vector.vector([d23*math.cos(a123), d23*math.sin(a123)]) ]
    solutions = []
    for p3 in p3s:
        solution = Configuration({v1:p1, v2:p2, v3:p3})
        solutions.append(solution)
    return solutions

class MergeCCH(Merge):
    """Represents a merging of two clusters and a hedgehog
       The first cluster determines the orientation of the resulting
       cluster
    """
    def __init__(self, c1, c2, hog, out):
        # init
        self.c1 = c1
        self.c2 = c2
        self.hog = hog
        self.output = out
        self._inputs = [c1, c2, hog]
        self._outputs = [out]
        self.overconstrained = False
        self.consistent = True
        MultiMethod.__init__(self)
        # check coincidence
        if hog.cvar not in c1.vars:
            raise Exception("hog.cvar not in c1.vars")
        if hog.cvar in c2.vars:
            raise Exception("hog.cvar in c2.vars")
        shared12 = Set(c1.vars).intersection(c2.vars)
        shared1h = Set(c1.vars).intersection(hog.xvars)
        shared2h = Set(c2.vars).intersection(hog.xvars)
        shared1 = shared12.union(shared1h)
        shared2 = shared12.union(shared2h)
        sharedh = shared1h.union(shared2h)
        if len(shared12) < 1:
            raise Exception("underconstrained c1 and c2")
        elif len(shared12) > 1:
            diag_print("overconstrained CCH - c1 and c2", "clmethods")
            self.overconstrained = True
        if len(shared1h) < 1:
            raise Exception("underconstrained c1 and hog")
        elif len(shared1h) > 1:
            diag_print("overconstrained CCH - c1 and hog", "clmethods")
            self.overconstrained = True
        if len(shared2h) < 1:
            raise Exception("underconstrained c2 and hog")
        elif len(shared2h) > 2:
            diag_print("overconstrained CCH - c2 and hog", "clmethods")
            self.overconstrained = True
        if len(shared1) < 1:
            raise Exception("underconstrained c1")
        elif len(shared1) > 1:
            diag_print("overconstrained CCH - c1", "clmethods")
            self.overconstrained = True
        if len(shared2) < 2:
            raise Exception("underconstrained c2")
        elif len(shared2) > 2:
            diag_print("overconstrained CCH - c2", "clmethods")
            self.overconstrained = True
        if len(sharedh) < 2:
            raise Exception("underconstrained hog")
        elif len(sharedh) > 2:
            diag_print("overconstrained CCH - hog", "clmethods")
            self.overconstrained = True

    #end __init__

    def __str__(self):
        s = "mergeCCH("+str(self.c1)+"+"+str(self.c2)+"+"+str(self.hog)+"->"+str(self.output)+")"
        s += "[" + self.status_str()+"]"
        return s

    def multi_execute(self, inmap):
        diag_print("MergeCCH.multi_execute called","clmethods")
        # assert hog.cvar in c1
        if self.hog.cvar in self.c1.vars:
            c1 = self.c1
            c2 = self.c2
        else:
            c1 = self.c2
            c2 = self.c1
        # get v1
        v1 = self.hog.cvar
        # get v2
        candidates2 = Set(self.hog.xvars).intersection(c1.vars).intersection(c2.vars)
        assert len(candidates2) >= 1
        v2 = list(candidates2)[0]
        # get v3
        candidates3 = Set(self.hog.xvars).intersection(c2.vars).difference([v1, v2])
        assert len(candidates3) >= 1
        v3 = list(candidates3)[0]
        # check
        assert v1 != v2
        assert v1 != v3
        assert v2 != v3
        # get configs
        confh = inmap[self.hog]
        conf1 = inmap[c1]
        conf2 = inmap[c2]
        # get angle
        p1h = confh.get(v1)
        p2h = confh.get(v2)
        p3h = confh.get(v3)
        a312 = angle_3p(p3h, p1h, p2h)
        # get distance d12
        p11 = conf1.get(v1)
        p21 = conf1.get(v2)
        d12 = distance_2p(p11, p21)
        # get distance d23
        p22 = conf2.get(v2)
        p32 = conf2.get(v3)
        d23 = distance_2p(p22, p32)
        adds = solve_add(v1,v2,v3,a312,d12,d23)
        solutions = []
        # do merge (note, order c1 c2 restored)
        conf1 = inmap[self.c1]
        conf2 = inmap[self.c2]
        for s in adds:
            solution = conf1.merge2D(s).merge2D(conf2)
            solutions.append(solution)
        return solutions

    def prototype_constraints(self):
        # assert hog.cvar in c1
        if self.hog.cvar in self.c1.vars:
            c1 = self.c1
            c2 = self.c2
        else:
            c1 = self.c2
            c2 = self.c1
        shared1h = Set(self.hog.xvars).intersection(c1.vars).difference([self.hog.cvar])
        shared2h = Set(self.hog.xvars).intersection(c2.vars).difference(shared1h)
        # get vars
        v1 = self.hog.cvar
        v2 = list(shared1h)[0]
        v3 = list(shared2h)[0]
        assert v1 != v2
        assert v1 != v3
        assert v2 != v3
        constraints = []
        constraints.append(NotAcuteConstraint(v2,v3,v1))
        constraints.append(NotObtuseConstraint(v2,v3,v1))
        return constraints

def solve_add(a,b,c, a_cab, d_ab, d_bc):
    diag_print("solve_dad: %s %s %s %f %f %f"%(a,b,c,a_cab,d_ab,d_bc),"clmethods")
    p_a = vector.vector([0.0,0.0])
    p_b = vector.vector([d_ab,0.0])
    dir = vector.vector([math.cos(-a_cab),math.sin(-a_cab)])
    solutions = cr_int(p_b, d_bc, p_a, dir)
    rval = []
    for s in solutions:
        p_c = s
        map = {a:p_a, b:p_b, c:p_c}
        rval.append(Configuration(map))
    return rval

class BalloonFromHogs(Merge):
    """Represent a balloon merged from two hogs"""
    def __init__(self, hog1, hog2, balloon):
        """Create a new balloon from two angles
        
           keyword args:
            hog1 - a Hedghog 
            hog2 - a Hedehog
            balloon - a Balloon instance
        """
        self.hog1 = hog1
        self.hog2 = hog2
        self.balloon = balloon
        self._inputs = [hog1, hog2]
        self._outputs = [balloon]
        self.overconstrained = False
        self.consistent = True
        MultiMethod.__init__(self)
        # check coincidence
        if hog1.cvar == hog2.cvar:
            raise Exception("hog1.cvar is hog2.cvar")
        shared12 = Set(hog1.xvars).intersection(hog2.xvars)
        if len(shared12) < 1:
            raise Exception("underconstrained")
        #elif len(shared12) > 1:
        #    raise Exception("overconstrained")

    def __str__(self):
        s = "hog2balloon("+str(self.hog1)+"+"+str(self.hog2)+"->"+str(self.balloon)+")"
        s += "[" + self.status_str()+"]"
        return s

    def multi_execute(self, inmap):
        diag_print("BalloonFromHogs.multi_execute called","clmethods")
        v1 = self.hog1.cvar
        v2 = self.hog2.cvar
        shared = Set(self.hog1.xvars).intersection(self.hog2.xvars).difference([v1,v2])
        v3 = list(shared)[0]
        assert v1 != v2
        assert v1 != v3
        assert v2 != v3
        # determine angle312
        conf1 = inmap[self.hog1]
        p31 = conf1.get(v3)
        p11 = conf1.get(v1)
        p21 = conf1.get(v2)
        a312 = angle_3p(p31,p11,p21)
        # determine distance d12
        d12 = 1.0
        # determine angle123
        conf2 = inmap[self.hog2]
        p12 = conf2.get(v1)
        p22 = conf2.get(v2)
        p32 = conf2.get(v3)
        a123 = angle_3p(p12,p22,p32)
        # solve
        return solve_ada(v1,v2,v3, a312, d12, a123)

def solve_ada(a, b, c, a_cab, d_ab, a_abc):
        diag_print("solve_ada: %s %s %s %f %f %f"%(a,b,c,a_cab,d_ab,a_abc),"clmethods")
        p_a = vector.vector([0.0,0.0])
        p_b = vector.vector([d_ab, 0.0])
        dir_ac = vector.vector([math.cos(-a_cab),math.sin(-a_cab)])
        dir_bc = vector.vector([-math.cos(-a_abc),math.sin(-a_abc)])
        if tol_eq(math.sin(a_cab), 0.0) and tol_eq(math.sin(a_abc),0.0):
            m = d_ab/2 + math.cos(-a_cab)*d_ab - math.cos(-a_abc)*d_ab
            p_c = vector.vector([m,0.0])
            # p_c = (p_a + p_b) / 2
            map = {a:p_a, b:p_b, c:p_c}
            cluster = _Configuration(map)
            cluster.underconstrained = True
            rval = [cluster]
        else:
            solutions = rr_int(p_a,dir_ac,p_b,dir_bc)
            rval = []
            for s in solutions:
                p_c = s
                map = {a:p_a, b:p_b, c:p_c}
                rval.append(Configuration(map))
        #endif
        return rval

class BalloonMerge(Merge):
    """Represents a merging of two balloons 
    """
    def __init__(self, in1, in2, out):
        self.input1 = in1
        self.input2 = in2
        self.output = out
        self.shared = list(Set(self.input1.vars).intersection(self.input2.vars))
        self._inputs = [in1, in2]
        self._outputs = [out]
        self.consistent = True
        MultiMethod.__init__(self)
        # check coincidence
        self.overconstrained = False
        shared = Set(in1.vars).intersection(in2.vars)
        if len(shared) < 2:
            raise Exception("underconstrained")
        elif len(shared) > 2:
            diag_print("overconstrained balloon merge", "clmethods")
            self.overconstrained = True

    def __str__(self):
        s = "balloonmerge("+str(self.input1)+"+"+str(self.input2)+"->"+str(self.output)+")"
        s += "[" + self.status_str()+"]"
        return s

    def multi_execute(self, inmap):
        diag_print("BalloonMerge.multi_execute called","clmethods")
        c1 = self._inputs[0]
        c2 = self._inputs[1]
        conf1 = inmap[c1]
        conf2 = inmap[c2]
        return [conf1.merge_scale_2D(conf2)]

class BalloonRigidMerge(Merge):
    """Represents a merging of a balloon and a cluster 
    """
    def __init__(self, balloon, cluster, output):
        self.balloon = balloon
        self.cluster= cluster
        self.output = output
        self.shared = list(Set(self.balloon.vars).intersection(self.cluster.vars))
        self._inputs = [balloon, cluster]
        self._outputs = [output]
        self.overconstrained = False
        self.consistent = True
        MultiMethod.__init__(self)
        # check coincidence
        shared = Set(balloon.vars).intersection(cluster.vars)
        if len(shared) < 2:
            raise Exception("underconstrained balloon-cluster merge")
        elif len(shared) > 2:
            diag_print("overconstrained merge "+str(balloon)+"&"+str(cluster), "clmethods")
            self.overconstrained = True

    def __str__(self):
        s = "balloonclustermerge("+str(self.balloon)+"+"+str(self.cluster)+"->"+str(self.output)+")"
        s += "[" + self.status_str()+"]"
        return s

    def multi_execute(self, inmap):
        diag_print("BalloonRigidMerge.multi_execute called","clmethods")
        rigid = inmap[self.cluster]
        balloon = inmap[self.balloon]
        return [rigid.merge_scale_2D(balloon)]
        #return [balloon.copy()]

class MergeHogs(Merge):
    """Represents a merging of two hogs to form a new hog
    """
    def __init__(self, hog1, hog2, output):
        self.hog1 = hog1
        self.hog2 = hog2
        self.output = output
        self._inputs = [hog1, hog2]
        self._outputs = [output]
        self.consistent = True
        MultiMethod.__init__(self)
        # check coincidence
        self.overconstrained = False
        if hog1.cvar != hog2.cvar:
            raise Exception("hog1.cvar != hog2.cvar")
        shared = Set(hog1.xvars).intersection(hog2.xvars)
        if len(shared) < 1:
            raise Exception("underconstrained balloon-cluster merge")
        elif len(shared) > 1:
            diag_print("overconstrained merge "+str(hog1)+"&"+str(hog2), "clmethods")
            self.overconstrained = True

    def __str__(self):
        s = "mergeHH("+str(self.hog1)+"+"+str(self.hog2)+"->"+str(self.output)+")"
        s += "[" + self.status_str()+"]"
        return s

    def multi_execute(self, inmap):
        diag_print("MergeHogs.multi_execute called","clmethods")
        conf1 = inmap[self._inputs[0]]
        conf2 = inmap[self._inputs[1]]
        shared = Set(self.hog1.xvars).intersection(self.hog2.xvars)
        conf12 = conf1.merge_scale_2D(conf2, [self.hog1.cvar, list(shared)[0]])
        return [conf12]


# ---------- derive methods -------

class Rigid2Hog(Derive):
    """Represents a derivation of a hog from a c)luster
    """
    def __init__(self, cluster, hog):
        self.cluster = cluster
        self.hog = hog
        self._inputs = [cluster]
        self._outputs = [hog]
        MultiMethod.__init__(self)

    def __str__(self):
        s = "rigid2hog("+str(self.cluster)+"->"+str(self.hog)+")"
        return s

    def multi_execute(self, inmap):
        diag_print("Rigid2Hog.multi_execute called","clmethods")
        conf1 = inmap[self._inputs[0]]
        vars = list(self._outputs[0].xvars) + [self._outputs[0].cvar]
        conf = conf1.select(vars)
        return [conf]

class Balloon2Hog(Derive):
    """Represents a derivation of a hog from a balloon
    """
    def __init__(self, balloon, hog):
        self.balloon = balloon
        self.hog = hog
        self._inputs = [balloon]
        self._outputs = [hog]
        MultiMethod.__init__(self)

    def __str__(self):
        s = "balloon2hog("+str(self.balloon)+"->"+str(self.hog)+")"
        return s

    def multi_execute(self, inmap):
        diag_print("Balloon2Hog.multi_execute called","clmethods")
        conf1 = inmap[self._inputs[0]]
        vars = list(self._outputs[0].xvars) + [self._outputs[0].cvar]
        conf = conf1.select(vars)
        return [conf]

class SubHog(Derive):
    def __init__(self, hog, sub):
        self.hog = hog
        self.sub = sub
        self._inputs = [hog]
        self._outputs = [sub]
        MultiMethod.__init__(self)

    def __str__(self):
        s = "subhog("+str(self.hog)+"->"+str(self.sub)+")"
        return s

    def multi_execute(self, inmap):
        diag_print("SubHog.multi_execute called","clmethods")
        conf1 = inmap[self._inputs[0]]
        vars = list(self._outputs[0].xvars) + [self._outputs[0].cvar]
        conf = conf1.select(vars)
        return [conf]

class PrototypeMethod(MultiMethod):

    def __init__(self, incluster, selclusters, outcluster, constraints):
        self._inputs = [incluster]+selclusters
        self._outputs = [outcluster]
        self._constraints = constraints
        MultiMethod.__init__(self)

    def multi_execute(self, inmap):
        diag_print("PrototypeMethod.multi_execute called","clmethods")
        incluster = self._inputs[0]
        selclusters = []
        for i in range(1,len(self._inputs)):
            selclusters.append(self._inputs[i])
        print("incluster", incluster)
        print("selclusters", map(str, selclusters))
        # get confs
        inconf = inmap[incluster]
        selmap = {}
        for cluster in selclusters:
            conf = inmap[cluster]
            assert len(conf.vars()) == 1
            var = conf.vars()[0]
            selmap[var] = conf.map[var]
        selconf = Configuration(selmap)
        sat = True
        print("inconf:",inconf)
        print("selconf:",selconf)
        for con in self._constraints:
            print("con:",con,)
            if con.satisfied(inconf.map) != con.satisfied(selconf.map):
                sat = False
            print(sat)
        if sat:
            return [inconf]
        else:
            return []
