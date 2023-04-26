import math
import random
import uuid

class Agent:
    def __init__(self, agentID, birthday, cell, metabolism=0, vision=0, maxAge=0, sugar=0, sex=None, fertilityAge=0, infertilityAge=0, tags=None, aggressionFactor=0):
        self.__id = agentID
        self.__born = birthday
        self.__cell = cell
        self.__metabolism = metabolism
        self.__vision = vision
        self.__sugar = sugar
        self.__startingSugar = sugar
        self.__alive = True
        self.__age = 0
        self.__maxAge = maxAge
        self.__cellsInVision = []
        self.__lastMoved = birthday
        self.__vonNeumannNeighbors = {"north": None, "south": None, "east": None, "west": None}
        self.__mooreNeighbors = {"north": None, "northeast": None, "northwest": None, "south": None, "southeast": None, "southwest": None, "east": None, "west": None}
        self.__socialNetwork = {}
        self.__parents = {"father": None, "mother": None}
        self.__children = []
        self.__friends = []
        self.__sex = sex
        self.__fertilityAge = fertilityAge
        self.__infertilityAge = infertilityAge
        self.__fertile = False
        self.__tags = tags
        self.__tribe = self.findTribe()
        self.__aggression = aggressionFactor
        self.__wealth = sugar
        # Debugging print statement
        #print("Agent stats: {0} vision, {1} metabolism, {2} max age, {3} initial wealth, {4} sex, {5} fertility age, {6} infertility age".format(self.__vision, self.__metabolism, self.__maxAge, self.__sugar, self.__sex, self.__fertilityAge, self.__infertilityAge))

    def addChildToCell(self, mate, cell, endowment):
        childMetabolism = endowment[0]
        childVision = endowment[1]
        childMaxAge = endowment[2]
        childStartingSugar = endowment[3]
        childSex = endowment[4]
        childFertilityAge = endowment[5]
        childInfertilityAge = endowment[6]
        childTags = endowment[7]
        childAggression = endowment[8]
        sugarscape = self.__cell.getEnvironment().getSugarscape()
        timestep = sugarscape.getTimestep()
        child = Agent(uuid.uuid4(), timestep, cell, childMetabolism, childVision, childMaxAge, childStartingSugar, childSex, childFertilityAge,
                      childInfertilityAge, childTags, childAggression)
        child.setCell(cell)
        sugarscape.addAgent(child)
        if self.__sex == "female":
            child.setMother(self)
            child.setFather(mate)
        else:
            child.setFather(self)
            child.setMother(mate)
        return child

    def addAgentToSocialNetwork(self, agentID):
        if agentID in self.__socialNetwork:
            return
        self.__socialNetwork[agentID] = {"lastSeen": self.__lastMoved, "timesVisited": 1, "timesReproduced": 0}

    def collectResourcesAtCell(self):
        if self.__cell != None:
            sugarCollected = self.__cell.getCurrSugar()
            self.__sugar = self.__sugar + sugarCollected
            self.__wealth = self.__sugar + sugarCollected
            self.__cell.doProductionPollution(sugarCollected)
            self.__cell.resetSugar()

    def doAging(self):
        if self.__alive == False:
            return
        self.__age += 1
        # Die if reached max age and if not infinitely-lived
        if self.__age >= self.__maxAge and self.__maxAge != -1:
            self.doDeath()

    def doCombat(self, cell):
        prey = cell.getAgent()
        if prey != None:
            maxCombatLoot = self.__cell.getEnvironment().getMaxCombatLoot()
            preyWealth = prey.getWealth()
            combatLoot = min(maxCombatLoot, preyWealth)
            self.__sugar += combatLoot
            self.__wealth += combatLoot
            prey.setSugar(preyWealth - combatLoot)
            prey.doDeath()
        self.setCell(cell)

    def doDeath(self):
        self.setAlive(False)
        self.unsetCell()
        livingChildren = []
        # Provide inheritance for living children
        # TODO: Determine complexity of other inheritance mechanisms in book (pg. 67)
        for child in self.__children:
            if child.isAlive() == True:
                livingChildren.append(child)
        if len(livingChildren) > 0:
            inheritancePerChild = math.floor(self.__wealth / len(livingChildren))
            for child in livingChildren:
                child.setSugar(child.getWealth() + inheritancePerChild)

    def doMetabolism(self):
        if self.__alive == False:
            return
        self.__sugar = self.__sugar - self.__metabolism
        self.__cell.doConsumptionPollution(self.__metabolism)
        if self.__sugar < 1:
            self.setAlive(False)
            self.unsetCell()

    def doReproduction(self):
        # Agent marked for removal should not reproduce
        if self.__alive == False:
            return
        random.seed(self.__cell.getEnvironment().getSugarscape().getSeed())
        neighborCells = self.__cell.getNeighbors()
        random.shuffle(neighborCells)
        emptyCells = self.findEmptyNeighborCells()
        for neighborCell in neighborCells:
            neighbor = neighborCell.getAgent()
            if neighbor != None:
                neighborCompatibility = self.isNeighborReproductionCompatible(neighbor)
                emptyCellsWithNeighbor = list(set(emptyCells + neighbor.findEmptyNeighborCells()))
                random.shuffle(emptyCellsWithNeighbor)
                if self.isFertile() == True and neighborCompatibility == True and len(emptyCellsWithNeighbor) != 0:
                    emptyCell = emptyCellsWithNeighbor.pop()
                    childEndowment = self.findChildEndowment(neighbor)
                    child = self.addChildToCell(neighbor, emptyCell, childEndowment)
                    self.__children.append(child)
                    childID = child.getID()
                    neighborID = neighbor.getID()
                    self.addAgentToSocialNetwork(childID)
                    neighbor.addAgentToSocialNetwork(childID)
                    neighbor.updateTimesVisitedFromAgent(self.__id, self.__lastMoved)
                    neighbor.updateTimesReproducedWithAgent(self.__id, self.__lastMoved)
                    self.updateTimesReproducedWithAgent(neighborID, self.__lastMoved)
                    self.__sugar -= math.ceil(self.__startingSugar / 2)
                    neighbor.setSugar(neighbor.getWealth() - math.ceil(neighbor.getStartingSugar() / 2))

    def doTagging(self):
        if self.__tags == None or self.__alive == False:
            return
        neighborCells = self.__cell.getNeighbors()
        random.seed(self.__cell.getEnvironment().getSugarscape().getSeed())
        random.shuffle(neighborCells)
        for neighborCell in neighborCells:
            neighbor = neighborCell.getAgent()
            if neighbor != None:
                position = random.randrange(len(self.__tags))
                neighbor.setTag(position, self.__tags[position])
                neighbor.setTribe(neighbor.findTribe())

    def doTimestep(self):
        timestep = self.__cell.getEnvironment().getSugarscape().getTimestep()
        # Prevent dead or already moved agent from moving
        if self.__alive == True and self.__lastMoved != timestep:
            self.__lastMoved = timestep
            self.moveToBestCellInVision()
            self.updateNeighbors()
            self.collectResourcesAtCell()
            self.doMetabolism()
            self.doTagging()
            self.doReproduction()
            self.doAging()

    def findAgentWealthAtCell(self, cell):
        agent = cell.getAgent()
        if agent == None:
            return 0
        else:
            return agent.getWealth()

    def findBestCellInVision(self):
        self.findCellsInVision()
        random.seed(self.__cell.getEnvironment().getSugarscape().getSeed())
        random.shuffle(self.__cellsInVision)
        bestCell = None
        bestRange = max(self.__cell.getEnvironment().getHeight(), self.__cell.getEnvironment().getWidth())
        bestSugar = 0
        agentX = self.__cell.getX()
        agentY = self.__cell.getY()
        combatMaxLoot = self.__cell.getEnvironment().getMaxCombatLoot()
        wraparound = self.__vision + 1
        for currCell in self.__cellsInVision:
            #currCell = self.__cellsInVision[i]
            # Either X or Y distance will be 0 due to cardinal direction movement only
            distanceX = (abs(agentX - currCell.getX()) % wraparound)
            distanceY = (abs(agentY - currCell.getY()) % wraparound)
            travelDistance = distanceX + distanceY
            if currCell.isOccupied() == True and self.__aggression == 0:
                continue
            # TODO: incorporate retaliation into combat decisionmaking (agent from same tribe as prey bigger than self in sight)
            agentInVision = currCell.getAgent()
            if agentInVision != None and agentInVision.getTribe() == self.__tribe:
                continue
            if bestCell == None:
                bestCell = currCell
                bestRange = travelDistance
                if agentInVision != None and agentInVision.getWealth() > self.__wealth:
                    print("Agent {0} too strong (wealth {1}) for agent {2} (wealth {3})".format(str(agentInVision), agentInVision.getWealth(), str(self), self.__wealth))
                    continue
                bestSugar = (bestCell.getCurrSugar() / (1 + bestCell.getCurrPollution())) + (self.__aggression * min(combatMaxLoot, self.findAgentWealthAtCell(currCell)))
            currSugar = (currCell.getCurrSugar() / (1 + currCell.getCurrPollution())) + (self.__aggression * min(combatMaxLoot, self.findAgentWealthAtCell(currCell)))
            # Move to closest cell with the most resources
            if currSugar > bestSugar or (currSugar == bestSugar and travelDistance < bestRange):
                bestCell = currCell
                bestRange = travelDistance
                if agentInVision != None and agentInVision.getWealth() > self.__wealth:
                    print("Agent {0} too strong (wealth {1}) for agent {2} (wealth {3})".format(str(agentInVision), agentInVision.getWealth(), str(self), self.__wealth))
                    continue
                bestSugar = (bestCell.getCurrSugar() / (1 + bestCell.getCurrPollution())) + (self.__aggression * min(combatMaxLoot, self.findAgentWealthAtCell(currCell)))
        if bestCell == None:
            bestCell = self.__cell
        return bestCell

    def findCellsInVision(self):
        if self.__vision > 0 and self.__cell != None:
            northCells = [self.__cell.getNorthNeighbor()]
            southCells = [self.__cell.getSouthNeighbor()]
            eastCells = [self.__cell.getEastNeighbor()]
            westCells = [self.__cell.getWestNeighbor()]
            # Vision 1 accounted for in list setup
            for i in range(self.__vision - 1):
                northCells.append(northCells[-1].getNorthNeighbor())
                southCells.append(southCells[-1].getSouthNeighbor())
                eastCells.append(eastCells[-1].getEastNeighbor())
                westCells.append(westCells[-1].getWestNeighbor())
            # Keep only unique cells
            self.setCellsInVision(list(set(northCells + southCells + eastCells + westCells)))

    def findChildEndowment(self, mate):
        random.seed(self.__cell.getEnvironment().getSugarscape().getSeed())
        parentMetabolisms = [self.__metabolism, mate.getMetabolism()]
        parentVisions = [self.__vision, mate.getVision()]
        parentMaxAges = [self.__maxAge, mate.getMaxAge()]
        parentInfertilityAges = [self.__infertilityAge, mate.getInfertilityAge()]
        parentFertilityAges = [self.__fertilityAge, mate.getFertilityAge()]
        parentSexes = [self.__sex, mate.getSex()]
        parentAggressionFactors = [self.__aggression, mate.getAggression()]
        startingSugar = math.ceil(self.__startingSugar / 2) + math.ceil(mate.getStartingSugar() / 2)

        childMetabolism = parentMetabolisms[random.randrange(2)]
        childVision = parentVisions[random.randrange(2)]
        childMaxAge = parentMaxAges[random.randrange(2)]
        # TODO: Determine if fertility/infertility age should be inherited or use global configuration as random range
        childInfertilityAge = parentInfertilityAges[random.randrange(2)]
        childFertilityAge = parentFertilityAges[random.randrange(2)]
        childSex = parentSexes[random.randrange(2)]
        childTags = []
        mateTags = mate.getTags()
        mismatchTags = [0, 1]
        for i in range(len(self.__tags)):
            if self.__tags[i] == mateTags[i]:
                childTags.append(self.__tags[i])
            else:
                childTags.append(mismatchTags[random.randrange(2)])
        childStartingSugar = startingSugar
        childAggression = parentAggressionFactors[random.randrange(2)]
        endowment = [childMetabolism, childVision, childMaxAge, childStartingSugar, childSex, childFertilityAge, childInfertilityAge, childTags, childAggression]
        return endowment

    def findEmptyNeighborCells(self):
        emptyCells = []
        neighborCells = self.__cell.getNeighbors()
        for neighborCell in neighborCells:
            if neighborCell.getAgent() == None:
                emptyCells.append(neighborCell)
        return emptyCells

    def findHammingDistanceInTags(self, neighbor):
        neighborTags = neighbor.getTags()
        hammingDistance = 0
        for i in range(len(self.__tags)):
            if self.__tags[i] != neighborTags[i]:
                hammingDistance += 1
        return hammingDistance

    def findTribe(self):
        if self.__tags == None:
            return None
        zeroes = 0
        tribeCutoff = math.floor(len(self.__tags) / 3)
        for tag in self.__tags:
            if tag == 0:
                zeroes += 1
        if zeroes < tribeCutoff + 1:
            return "green"
        elif zeroes < (2 * tribeCutoff) + 1:
            return "blue"
        else:
            return "red"

    def getAge(self):
        return self.__age

    def getAggression(self):
        return self.__aggression

    def getAlive(self):
        return self.__alive

    def getCell(self):
        return self.__cell

    def getCellsInVision(self):
        return self.__cellsInVision

    def getEnvironment(self):
        return self.__cell.getEnvironment()

    def getInfertilityAge(self):
        return self.__infertilityAge

    def getFather(self):
        return self.__parents["father"]

    def getFertile(self):
        return self.__fertile

    def getFertilityAge(self):
        return self.__fertilityAge

    def getID(self):
        return self.__id

    def getMaxAge(self):
        return self.__maxAge

    def getMetabolism(self):
        return self.__metabolism

    def getMooreNeighbors(self):
        return self.__mooreNeighbors

    def getMother(self):
        return self.__parents["mother"]

    def getSex(self):
        return self.__sex

    def getSocialNetwork(self):
        return self.__socialNetwork

    def getStartingSugar(self):
        return self.__startingSugar

    def getSugar(self):
        return self.__sugar

    def getTag(self, position):
        return self.__tags[position]

    def getTags(self):
        return self.__tags

    def getTribe(self):
        return self.__tribe

    def getVision(self):
        return self.__vision

    def getVonNeumannNeighbors(self):
        return self.__vonNeumannNeigbbors

    def getWealth(self):
        return self.__sugar

    def isAlive(self):
        return self.getAlive()

    def isFertile(self):
        if self.__sugar >= self.__startingSugar and self.__age >= self.__fertilityAge and self.__age < self.__infertilityAge:
            return True
        return False

    def isNeighborReproductionCompatible(self, neighbor):
        if neighbor == None:
            return False
        neighborSex = neighbor.getSex()
        neighborFertility = neighbor.isFertile()
        if self.__sex == "female" and (neighborSex == "male" and neighborFertility == True):
            return True
        elif self.__sex == "male" and (neighborSex == "female" and neighborFertility == True):
            return True
        else:
            return False

    def moveToBestCellInVision(self):
        bestCell = self.findBestCellInVision()
        if self.__aggression > 0:
            self.doCombat(bestCell)
        else:
            self.setCell(bestCell)

    def setAge(self, age):
        self.__age = age

    def setAggression(self, aggression):
        self.__aggression = aggression

    def setAlive(self, alive):
        self.__alive = alive
    
    def setCell(self, cell):
        if(self.__cell != None):
            self.unsetCell()
        self.__cell = cell
        self.__cell.setAgent(self)

    def setCellsInVision(self, cells):
        self.__cellsInVision = cells

    def setInfertilityAge(self, infertilityAge):
        self.__infertilityAge = infertilityAge

    def setFather(self, father):
        self.__parents["father"] = father
        self.__socialNetwork[father.getID()] = {"lastSeen": self.__lastMoved, "timesVisited": 1, "timesReproduced": 0}

    def setFertile(self, fertile):
        self.__fertile = fertile

    def setFertilityAge(self, fertilityAge):
        self.__fertilityAge = fertilityAge

    def setID(self, agentID):
        self.__id = agentID

    def setMaxAge(self, maxAge):
        self.__maxAge = maxAge

    def setMetabolism(self, metabolism):
        self.__metabolism = metabolism

    def setMooreNeighbors(self, mooreNeighbors):
        self.__mooreNeighbors = mooreNeighbors

    def setMother(self, mother):
        self.__parents["mother"] = mother
        self.__socialNetwork[mother.getID()] = {"lastSeen": self.__lastMoved, "timesVisited": 1, "timesReproduced": 0}

    def setSex(self, sex):
        self.__sex = sex

    def setSocialNetwork(self, socialNetwork):
        self.__socialNetwork = socialNetwork

    def setSugar(self, sugar):
        self.__sugar = sugar

    def setTag(self, position, value):
        self.__tags[position] = value

    def setTags(self, tags):
        self.__tags = tags

    def setTribe(self, tribe):
        self.__tribe = tribe

    def setVision(self, vision):
        self.__vision = vision
 
    def setVonNeumannNeighbors(self, vonNeumannNeigbors):
        self.__vonNeumannNeighbors = vonNeumannNeighbors

    def setWealth(self, wealth):
        self.__wealth = wealth

    def updateFriends(self, neighbor):
        neighborID = neighbor.getID()
        neighborHammingDistance = self.findHammingDistanceInTags(neighbor)
        neighborEntry = {"friend": neighborID, "hammingDistance": neighborHammingDistance}
        # TODO: Make max number of friends configurable, using book definition (pg. 80)
        if len(self.__friends) < 5:
            self.__friends.append(neighborEntry)
        else:
            maxHammingDistance = 0
            maxDifferenceFriend = None
            for friend in self.__friends:
                # If already a friend, update Hamming Distance
                if friend["friend"] == neighborID:
                    self.__friends.remove(friend)
                    self.__friends.append(neighborEntry)
                    return
                if friend["hammingDistance"] > maxHammingDistance:
                    maxDistanceFriend = friend
                    maxHammingDistance = friend["hammingDistance"]
            if maxHammingDistance > neighborHammingDistance:
                self.__friends.remove(maxDistanceFriend)
                self.__friends.append(neighborEntry)

    def updateMooreNeighbors(self):
        for direction, neighbor in self.__vonNeumannNeighbors.items():
            self.__mooreNeighbors[direction] = neighbor
        north = self.__mooreNeighbors["north"]
        south = self.__mooreNeighbors["south"]
        east = self.__mooreNeighbors["east"]
        west = self.__mooreNeighbors["west"]
        self.__mooreNeighbors["northeast"] = north.getCell().getEastNeighbor() if north != None else None
        self.__mooreNeighbors["northeast"] = east.getCell().getNorthNeighbor() if east != None and self.__mooreNeighbors["northeast"] == None else None
        self.__mooreNeighbors["northwest"] = north.getCell().getWestNeighbor() if north != None else None
        self.__mooreNeighbors["northwest"] = west.getCell().getNorthNeighbor() if west != None and self.__mooreNeighbors["northwest"] == None else None
        self.__mooreNeighbors["southeast"] = south.getCell().getEastNeighbor() if south != None else None
        self.__mooreNeighbors["southeast"] = east.getCell().getSouthNeighbor() if east != None and self.__mooreNeighbors["southeast"] == None else None
        self.__mooreNeighbors["southwest"] = south.getCell().getWestNeighbor() if south != None else None
        self.__mooreNeighbors["southwest"] = west.getCell().getSouthNeighbor() if west != None and self.__mooreNeighbors["southwest"] == None else None

    def updateNeighbors(self):
        self.updateVonNeumannNeighbors()
        self.updateMooreNeighbors()
        self.updateSocialNetwork()

    def updateSocialNetwork(self):
        for direction, neighbor in self.__vonNeumannNeighbors.items():
            if neighbor == None:
                continue
            neighborID = neighbor.getID()
            if neighborID in self.__socialNetwork:
                self.updateTimesVisitedFromAgent(neighborID, self.__lastMoved)
            else:
                self.addAgentToSocialNetwork(neighborID)
            self.updateFriends(neighbor)

    def updateTimesReproducedWithAgent(self, agentID, timestep):
        if agentID not in self.__socialNetwork:
            self.addToSocialNetwork(agentID)
            self.updateTimesReproducedWithAgent(agentID, timestep)
        else:
            self.__socialNetwork[agentID]["timesReproduced"] += 1
            self.__socialNetwork[agentID]["lastSeen"] = timestep

    def updateTimesVisitedFromAgent(self, agentID, timestep):
        if agentID not in self.__socialNetwork:
            self.addAgentToSocialNetwork(agentID)
        else:
            self.__socialNetwork[agentID]["timesVisited"] += 1
            self.__socialNetwork[agentID]["lastSeen"] = timestep

    def updateVonNeumannNeighbors(self):
        self.__vonNeumannNeighbors["north"] = self.__cell.getNorthNeighbor().getAgent()
        self.__vonNeumannNeighbors["south"] = self.__cell.getSouthNeighbor().getAgent()
        self.__vonNeumannNeighbors["east"] = self.__cell.getEastNeighbor().getAgent()
        self.__vonNeumannNeighbors["west"] = self.__cell.getWestNeighbor().getAgent()

    def unsetCell(self):
        self.__cell.unsetAgent()
        self.__cell = None

    def __str__(self):
        return "{0}".format(self.__id)
