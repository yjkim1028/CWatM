# -------------------------------------------------------------------------
# Name:        Waterdemand module
# Purpose:
#
# Author:      PB
#
# Created:     15/07/2016
# Copyright:   (c) PB 2016
# -------------------------------------------------------------------------

from management_modules.data_handling import *


class waterdemand(object):

    """
    WATERDEMAND
    calculating water demand
    Industrial, domenstic based on precalculated maps
    Agricultural water demand based on water need by plants
    """

    def __init__(self, waterdemand_variable):
        self.var = waterdemand_variable

# --------------------------------------------------------------------------
# --------------------------------------------------------------------------

    def initial(self):
        """
        Initial part of the water demand module
        Set the water allocation
        """
        if checkOption('includeWaterDemand'):

            # Add  zones at which water allocation (surface and groundwater allocation) is determined
            if checkOption('usingAllocSegments'):
               self.var.allocSegments = loadmap('allocSegments').astype(np.int)
               self.var.segmentArea = npareatotal(self.var.cellArea, self.var.allocSegments)

            # partitioningGroundSurfaceAbstraction
            # partitioning abstraction sources: groundwater and surface water
            # partitioning based on local average baseflow (m3/s) and upstream average discharge (m3/s)
            # estimates of fractions of groundwater and surface water abstractions

            averageBaseflowInput = loadmap('averageBaseflow')
            averageDischargeInput = loadmap('averageDischarge')

            # convert baseflow from m to m3/s
            if returnBool('baseflowInM'):
                averageBaseflowInput = averageBaseflowInput * self.var.cellArea * self.var.InvDtSec

            if checkOption('usingAllocSegments'):
                averageBaseflowInput = npareaaverage(averageBaseflowInput, self.var.allocSegments)
                averageUpstreamInput = npareamaximum(averageDischargeInput, self.var.allocSegments)

            swAbstractionFraction = np.maximum(0.0, np.minimum(1.0, averageDischargeInput / np.maximum(1e-20, averageDischargeInput + averageBaseflowInput)))
            swAbstractionFraction = np.minimum(1.0, np.maximum(0.0, swAbstractionFraction))
            # self.var.swAbstractionFraction[np.isnan(self.var.swAbstractionFraction)] = 0
            # self.var.swAbstractionFraction = np.round(self.var.swAbstractionFraction,2)


            self.var.swAbstractionFraction = globals.inZero.copy()
            for No in xrange(4):
                self.var.swAbstractionFraction += self.var.fracVegCover[No] * swAbstractionFraction
            for No in xrange(4,6):
                self.var.swAbstractionFraction += self.var.fracVegCover[No]
            ii =1

            # init unmetWaterDemand -> to calculate actual one the the unmet water demand from previous day is needed
            self.var.unmetDemandPaddy = self.var.init_module.load_initial('unmetDemandPaddy')
            self.var.unmetDemandNonpaddy = self.var.init_module.load_initial('unmetDemandNonpaddy')
            #self.var.unmetDemandPaddy = globals.inZero.copy()
            #self.var.unmetDemandNonpaddy = globals.inZero.copy()


            # for Xiaogang's agent model
            self.var.alphaDepletion = 1.0
            if "alphaDepletion" in binding:
                self.var.alphaDepletion = loadmap('alphaDepletion')



        else:  # no water demand
            self.var.nonIrrGrossDemand = 0
            self.var.nonIrrReturnFlowFraction = 0
            self.var.nonFossilGroundwaterAbs = 0



            self.var.sumIrrGrossDemand = 0
            self.var.waterWithdrawal = 0
            self.var.act_irrGrossWithdrawal = 0
            self.var.unmetDemand = 0

            self.var.unmetDemandPaddy = globals.inZero.copy()
            self.var.unmetDemandNonpaddy = globals.inZero.copy()




            # ---------------------------------------------------------------------------------------
    # report(decompress(self.var.discharge), "C:\work\output/q1.map")



# --------------------------------------------------------------------------

    def dynamic(self):
        """
        Dynamic part of the water demand module

        * calculate the fraction of water from surface water vs. groundwater
        * get non-Irrigation GROSS water demand and its return flow fraction
        """

        #


        if checkOption('includeWaterDemand'):

            if (dateVar['curr'] >= 137):
                ii =1

            # ----------------------------------------------------
            # WATER AVAILABILITY

            if checkOption('use_environflow'):
                if dateVar['newStart'] or dateVar['newMonth']:
                    # envflow in [m3/s] -> [m]
                    self.var.envFlowm3s = readnetcdf2('EnvironmentalFlowFile', dateVar['currDate'],"month", cut = self.var.cut_ef_map) # in [m3/s]
                    #self.var.envFlow = self.var.M3toM * self.var.DtSec * self.var.envFlow
                    self.var.envFlow = self.var.M3toM  * self.var.channelAlpha * self.var.chanLength * self.var.envFlowm3s  ** 0.6 # in [m]
            else:
                self.var.envFlow = 0.0

            # to avoid small values and to avoid surface water abstractions from dry channels (>= 0.5mm)
            self.var.readAvlChannelStorageM = np.where(self.var.channelStorage < (0.0005 * self.var.cellArea), 0., self.var.channelStorage)  # in [m3]
            # coversersion m3 -> m # minus environmental flow
            self.var.readAvlChannelStorageM = self.var.readAvlChannelStorageM * self.var.M3toM  # in [m]
            self.var.readAvlChannelStorageM = np.maximum(0.,self.var.readAvlChannelStorageM - self.var.envFlow)






            # ----------------------------------------------------
            # WATER DEMAND

            # industry water demand
            if dateVar['newStart'] or dateVar['newYear']:
                self.var.industryGrossDemand = readnetcdf2('industryWaterDemandFile', dateVar['currDate'], "yearly", value="industryGrossDemand")
                self.var.industryNettoDemand = readnetcdf2('industryWaterDemandFile', dateVar['currDate'], "yearly", value="industryNettoDemand")
                self.var.industryGrossDemand = np.where(self.var.industryGrossDemand > self.var.InvCellArea, self.var.industryGrossDemand, 0.0)
                self.var.industryNettoDemand = np.where(self.var.industryNettoDemand > self.var.InvCellArea, self.var.industryNettoDemand, 0.0)

            # domestic water demand
            if dateVar['newStart'] or dateVar['newMonth']:
                self.var.domesticGrossDemand = readnetcdf2('domesticWaterDemandFile', dateVar['currDate'], "monthly", value="domesticGrossDemand")
                self.var.domesticNettoDemand = readnetcdf2('domesticWaterDemandFile', dateVar['currDate'], "monthly", value="domesticNettoDemand")
                # avoid small values (less than 1 m3):
                self.var.domesticGrossDemand = np.where(self.var.domesticGrossDemand > self.var.InvCellArea, self.var.domesticGrossDemand, 0.0)
                self.var.domesticNettoDemand = np.where(self.var.domesticNettoDemand > self.var.InvCellArea, self.var.domesticNettoDemand, 0.0)

                # total (potential) non irrigation water demand
                self.var.nonIrrGrossDemand = self.var.domesticGrossDemand + self.var.industryGrossDemand
                self.var.nonIrrNettoDemand = np.minimum(self.var.nonIrrGrossDemand, self.var.domesticNettoDemand + self.var.industryNettoDemand)

                # fraction of return flow from domestic and industrial water demand
                self.var.nonIrrReturnFlowFraction = divideValues((self.var.nonIrrGrossDemand - self.var.nonIrrNettoDemand), self.var.nonIrrGrossDemand)




            # from irrigation
            #-----------------
            # Paddy irrigation -> No = 2
            # Non paddy irrigation -> No = 3

            # irrigation water demand for paddy
            No = 2
            self.var.irrGrossDemand[No] = 0.0
            # a function of cropKC (evaporation and transpiration) and available water see Wada et al. 2014 p. 19
            self.var.irrGrossDemand[No] = np.where(self.var.cropKC[No] > 0.75, np.maximum(0.,(self.var.alphaDepletion * self.var.maxtopwater - (self.var.topwater + self.var.availWaterInfiltration[
                No]))), 0.)
            # ignore demand if less than 1 m3
            self.var.irrGrossDemand[No] = np.where(self.var.irrGrossDemand[No] > self.var.InvCellArea, self.var.irrGrossDemand[No], 0)


            # irrNonPaddy
            No = 3

            # Infiltration capacity
            #  ========================================
            # first 2 soil layers to estimate distribution between runoff and infiltration
            soilWaterStorage = self.var.w1[No] + self.var.w2[No]
            soilWaterStorageCap = self.var.ws1[No] + self.var.ws2[No]
            relSat = soilWaterStorage / soilWaterStorageCap
            satAreaFrac = 1 - (1 - relSat) ** self.var.arnoBeta[No]
            satAreaFrac = np.maximum(np.minimum(satAreaFrac, 1.0), 0.0)

            store = soilWaterStorageCap / (self.var.arnoBeta[No] + 1)
            potBeta = (self.var.arnoBeta[No] + 1) / self.var.arnoBeta[No]
            potInf = store - store * (1 - (1 - satAreaFrac) ** potBeta)


            # ----------------------------------------------------------



            availWaterPlant1 = np.maximum(0., self.var.w1[No] - self.var.wwp1[No]) * self.var.rootDepth[0][No]
            availWaterPlant2 = np.maximum(0., self.var.w2[No] - self.var.wwp2[No]) * self.var.rootDepth[1][No]
            #availWaterPlant3 = np.maximum(0., self.var.w3[No] - self.var.wwp3[No]) * self.var.rootDepth[2][No]
            readAvlWater = availWaterPlant1 + availWaterPlant2 # + availWaterPlant3

            # calculate   ****** SOIL WATER STRESS ************************************

            #The crop group number is a indicator of adaptation to dry climate,
            # e.g. olive groves are adapted to dry climate, therefore they can extract more water from drying out soil than e.g. rice.
            # The crop group number of olive groves is 4 and of rice fields is 1
            # for irrigation it is expected that the crop has a low adaptation to dry climate
            #cropGroupNumber = 1.0
            etpotMax = np.minimum(0.1 * (self.var.totalPotET[No] * 1000.),1.0)
            # to avoid a strange behaviour of the p-formula's, ETRef is set to a maximum of 10 mm/day.


            # for group number 1 -> those are plants which needs irrigation
            # p = 1 / (0.76 + 1.5 * np.minimum(0.1 * (self.var.totalPotET[No] * 1000.), 1.0)) - 0.10 * ( 5 - cropGroupNumber)
            p = 1 / (0.76 + 1.5 * etpotMax) - 0.4
            # soil water depletion fraction (easily available soil water) # Van Diepen et al., 1988: WOFOST 6.0, p.87.
            p = p + (etpotMax - 0.6) / 4
            # correction for crop group 1  (Van Diepen et al, 1988) -> p between 0.14 - 0.77
            p = np.maximum(np.minimum(p, 1.0), 0.)
            # p is between 0 and 1 => if p =1 wcrit = wwp, if p= 0 wcrit = wfc
            # p is closer to 0 if evapo is bigger and cropgroup is smaller

            wCrit1 = ((1 - p) * (self.var.wfc1[No] - self.var.wwp1[No])) + self.var.wwp1[No]
            wCrit2 = ((1 - p) * (self.var.wfc2[No] - self.var.wwp2[No])) + self.var.wwp2[No]
            wCrit3 = ((1 - p) * (self.var.wfc3[No] - self.var.wwp3[No])) + self.var.wwp3[No]

            critWaterPlant1 = np.maximum(0., wCrit1 - self.var.wwp1[No]) * self.var.rootDepth[0][No]
            critWaterPlant2 = np.maximum(0., wCrit2 - self.var.wwp2[No]) * self.var.rootDepth[1][No]
            #critWaterPlant3 = np.maximum(0., wCrit3 - self.var.wwp3[No]) * self.var.rootDepth[2][No]
            critAvlWater = critWaterPlant1 + critWaterPlant2 # + critWaterPlant3

            # with alpha from Xiaogang He, to adjust irrigation to farmer's need
            self.var.irrGrossDemand[No] = np.where(self.var.cropKC[No] > 0.20, np.where(readAvlWater < self.var.alphaDepletion * critAvlWater,
                                                            np.maximum(0.0, self.var.alphaDepletion * self.var.totAvlWater - readAvlWater),  0.), 0.)
            # should not be bigger than infiltration capacity
            self.var.irrGrossDemand[No] = np.minimum(self.var.irrGrossDemand[No],potInf)

            # ignore demand if less than 1 m3
            self.var.irrGrossDemand[No] = np.where(self.var.irrGrossDemand[No] > self.var.InvCellArea, self.var.irrGrossDemand[No], 0)

            # Sum up irrigation water demand
            self.var.sumIrrGrossDemand = self.var.fracVegCover[2] * self.var.irrGrossDemand[2] + self.var.fracVegCover[3] * self.var.irrGrossDemand[3]
            irrPaddyDemand = self.var.fracVegCover[2] * self.var.irrGrossDemand[2]
            irrNonpaddyDemand = self.var.fracVegCover[3] * self.var.irrGrossDemand[3]

            # Sum up water demand
            # totalGrossDemand [m]: total maximum (potential) water demand: irrigation and non irrigation
            totalPotGrossDemand = self.var.nonIrrGrossDemand + self.var.sumIrrGrossDemand  # in [m]


            # surface water abstraction that can be extracted to fulfill totalGrossDemand
            # - based on ChannelStorage and swAbstractionFraction * totalPotGrossDemand
            # sum up potentiel surface water abstraction (no groundwater abstraction under water and sealed area)
            potSurfaceAbstract = totalPotGrossDemand * self.var.swAbstractionFraction





            # WATER DEMAND vs. WATER AVAILABILITY
            #-------------------------------------

            if not(checkOption('usingAllocSegments')):
                # only local surface water abstraction is allowed (network is only within a cell)
                self.var.actSurfaceWaterAbstract = np.minimum(self.var.readAvlChannelStorageM, potSurfaceAbstract)
                # if surface water is not sufficient it is taken from groundwater


                if checkOption('includeWaterBodies'):
                    #self.var.potGroundwaterAbstract = totalPotGrossDemand - self.var.actSurfaceWaterAbstract
                    #realswAbstractionFraction = divideValues(self.var.actSurfaceWaterAbstract, totalPotGrossDemand)

                    remainNeed = potSurfaceAbstract - self.var.actSurfaceWaterAbstract


                    # first from big Lakes and reservoirs, not as easy because big lakes cover several gridcells
                    # collect all water deamnd from lake pixels of same id
                    remainNeedBig = npareatotal(remainNeed, self.var.waterBodyID)
                    remainNeedBigC = np.compress(self.var.compress_LR, remainNeedBig)

                    # Storage of a big lake
                    lakeResStorageC = np.where(self.var.waterBodyTypCTemp == 0, 0.,
                                np.where(self.var.waterBodyTypCTemp == 1, self.var.lakeStorageM3C, self.var.reservoirStorageM3C)) / self.var.MtoM3C
                    minlake =  np.maximum(0., lakeResStorageC - 0.99 *  lakeResStorageC)
                    actbigLakeAbstC =  np.minimum(minlake , remainNeedBigC)
                    # substract from both, because it is sorted by self.var.waterBodyTypCTemp
                    self.var.lakeStorageM3C = self.var.lakeStorageM3C - actbigLakeAbstC * self.var.MtoM3C
                    self.var.reservoirStorageM3C = self.var.reservoirStorageM3C - actbigLakeAbstC * self.var.MtoM3C
                    bigLakesFactorC = divideValues(actbigLakeAbstC , remainNeedBigC)

                    # and back to the big array
                    bigLakesFactor = globals.inZero.copy()
                    np.put(bigLakesFactor, self.var.decompress_LR, bigLakesFactorC)
                    bigLakesFactorAllaroundlake = npareamaximum(bigLakesFactor, self.var.waterBodyID)
                    # abstraction from big lakes is partioned to the users around the lake
                    self.var.actbigLakeResAbst = remainNeed * bigLakesFactorAllaroundlake

                    # remaining need is used from small lakes
                    remainNeed1 = remainNeed  * (1 - bigLakesFactorAllaroundlake)
                    minlake = np.maximum(0.,self.var.smalllakeStorageM3 - self.var.minsmalllakeStorageM3) * self.var.M3toM
                    self.var.actsmallLakeResAbst = np.minimum(minlake, remainNeed1)
                    #self.var.actLakeResAbst = np.minimum(0.5 * self.var.smalllakeStorageM3 * self.var.M3toM, remainNeed)
                    # actsmallLakesres is substracted from small lakes storage
                    self.var.smalllakeStorageM3 = self.var.smalllakeStorageM3 - self.var.actsmallLakeResAbst * self.var.MtoM3


                    # remaining is taken from groundwater if possible
                    remainNeed2 = potSurfaceAbstract - (self.var.actSurfaceWaterAbstract + self.var.actbigLakeResAbst + self.var.actsmallLakeResAbst)
                    self.var.potGroundwaterAbstract = totalPotGrossDemand - (self.var.actSurfaceWaterAbstract + self.var.actsmallLakeResAbst)
                    # real surface water abstraction can be lower, because not all demand can be done from surface water
                    realswAbstractionFraction = divideValues(self.var.actSurfaceWaterAbstract + self.var.actsmallLakeResAbst, totalPotGrossDemand)
                else:
                    self.var.potGroundwaterAbstract = totalPotGrossDemand - self.var.actSurfaceWaterAbstract
                    realswAbstractionFraction = divideValues(self.var.actSurfaceWaterAbstract, totalPotGrossDemand)




                # calculate renewableAvlWater (non-fossil groundwater and channel) - environmental flow
                self.var.renewableAvlWater = self.var.readAvlStorGroundwater + self.var.readAvlChannelStorageM
            else:
                ii =0

            self.var.nonFossilGroundwaterAbs = np.minimum(self.var.readAvlStorGroundwater,  self.var.potGroundwaterAbstract)




            # if limitAbstraction from groundwater is True
            # - no fossil gwAbstraction and water demand may be reduced
            # variable to reduce/limit groundwater abstraction (> 0 if limitAbstraction = True)
            if checkOption('limitAbstraction'):

                # Fossil groundwater abstraction is not allowed
                # allocation rule here: domestic& industry > irrigation > paddy

                # nonirrgated demand: adjusted (and maybe increased) by gwabstration factor
                nonIrrGrossDemandGW = self.var.nonIrrGrossDemand  * (1- realswAbstractionFraction)

                # if nonirrgated water demand is higher than actual growndwater abstraction (wwhat is needed and what is stored in gw)
                nonIrrGrossDemandGW  = np.where(nonIrrGrossDemandGW > self.var.nonFossilGroundwaterAbs, self.var.nonFossilGroundwaterAbs, nonIrrGrossDemandGW)
                self.var.act_nonIrrGrossWithdrawal = realswAbstractionFraction * self.var.nonIrrGrossDemand + nonIrrGrossDemandGW


                sum_irrGrossDemandGW = self.var.sumIrrGrossDemand  * (1- realswAbstractionFraction)
                sum_irrGrossDemandGW = np.minimum(self.var.nonFossilGroundwaterAbs - nonIrrGrossDemandGW, sum_irrGrossDemandGW)
                self.var.act_irrGrossWithdrawal = realswAbstractionFraction * self.var.sumIrrGrossDemand + sum_irrGrossDemandGW

                # nonpaddy
                irrnonpaddyGW = self.var.fracVegCover[3] * (1- realswAbstractionFraction) * self.var.irrGrossDemand[3]
                irrnonpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs - nonIrrGrossDemandGW, irrnonpaddyGW)
                self.var.act_irrNonpaddyWithdrawal = self.var.fracVegCover[3] * realswAbstractionFraction * self.var.irrGrossDemand[3]  +  irrnonpaddyGW
                # paddy
                irrpaddyGW = self.var.fracVegCover[2] * (1 - realswAbstractionFraction) * self.var.irrGrossDemand[2]
                irrpaddyGW = np.minimum(self.var.nonFossilGroundwaterAbs - nonIrrGrossDemandGW - irrnonpaddyGW, irrpaddyGW)
                self.var.act_irrPaddyWithdrawal = self.var.fracVegCover[2] * realswAbstractionFraction * self.var.irrGrossDemand[2]  +  irrpaddyGW

                # back to non fraction values
                self.var.irrGrossDemand[2] = divideValues(self.var.act_irrPaddyWithdrawal, self.var.fracVegCover[2])
                self.var.irrGrossDemand[3] = divideValues(self.var.act_irrNonpaddyWithdrawal, self.var.fracVegCover[3])

            else:
                # Fossil groundwater abstractions are allowed
                ii =1
                self.var.act_nonIrrGrossWithdrawal = self.var.nonIrrGrossDemand
                self.var.act_irrGrossWithdrawal = self.var.sumIrrGrossDemand
                self.var.act_irrNonpaddyWithdrawal = self.var.fracVegCover[3] * self.var.irrGrossDemand[3]
                self.var.act_irrPaddyWithdrawal = self.var.fracVegCover[2] * self.var.irrGrossDemand[2]

            if (dateVar['curr'] == 116):
                ii = 1


            # calculate real water demand, because irr demand has still demand from previous day included
            self.var.act_demandIrrPaddy = np.maximum(0, irrPaddyDemand - self.var.unmetDemandPaddy)
            self.var.act_demandIrrNonpaddy = np.maximum(0, irrNonpaddyDemand - self.var.unmetDemandNonpaddy)
            self.var.waterDemand =  self.var.act_demandIrrPaddy  + self.var.act_demandIrrNonpaddy + self.var.nonIrrGrossDemand
            self.var.waterWithdrawal = self.var.act_nonIrrGrossWithdrawal + self.var.act_irrGrossWithdrawal

            # unmet is either potGroundwaterAbstract - self.var.nonFossilGroundwaterAbs or demand - withdrawal
            #self.var.unmetDemand = np.maximum(0.0, self.var.potGroundwaterAbstract - self.var.nonFossilGroundwaterAbs)
            self.var.unmetDemand = (self.var.sumIrrGrossDemand - self.var.act_irrGrossWithdrawal) + (self.var.nonIrrGrossDemand - self.var.act_nonIrrGrossWithdrawal)
            self.var.unmetDemandPaddy = irrPaddyDemand - self.var.act_irrPaddyWithdrawal
            self.var.unmetDemandNonpaddy = irrNonpaddyDemand - self.var.act_irrNonpaddyWithdrawal







            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.nonIrrGrossDemand, self.var.sumIrrGrossDemand],  # In
                    [self.var.nonFossilGroundwaterAbs, self.var.unmetDemand, self.var.actSurfaceWaterAbstract],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand1", False)


            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.waterWithdrawal],  # In
                    [self.var.nonFossilGroundwaterAbs, self.var.actSurfaceWaterAbstract],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand2", False)


            if checkOption('calcWaterBalance'):
                self.var.waterbalance_module.waterBalanceCheck(
                    [self.var.act_irrGrossWithdrawal],  # In
                    [self.var.fracVegCover[2]* self.var.irrGrossDemand[2], self.var.fracVegCover[3]* self.var.irrGrossDemand[3]],  # Out
                    [globals.inZero],
                    [globals.inZero],
                    "Waterdemand4", True)



