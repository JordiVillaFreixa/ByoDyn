#
#  Project: ByoDyn
#
#  Copyright (C) 2008 Alex Gomez-Garrido, Adrian L. Garcia-Lomana and Jordi Villa-Freixa
#
#  Author: Alex Gomez-Garrido
#
#  Created: 2007-04-04 by Alex Gomez-Garrido
#
#  This application is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public
#  License as published by the Free Software Foundation; either
#  version 2 of the License, or (at your option) any later version.
#
#  This application is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Library General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with this library; if not, write to the Free
#  Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111 USA.
# 

# $Id: simulatorOpenModelica.py,v 4.4 2008/12/03 16:37:38 alglomana Exp $

## \file
# This module simulates the model in the case the integration option OpenModelica has been selected.

import os, re, sys
import formulas, initiator, errorMessages, sbmlWorker
from affectors import *

class ClassSimulatorOpenModelica:

    '''
    Class for the OpenModelica simulator.
    '''    

    def __init__(self):
        
	'''
        The constructor.
        '''
    
        return None

    def createInput(self, metamodel, model, outputfiles):
    
        '''
	This method creates the input files for the openModelica simulator.
	'''
        #/ 1.- writting the openModelica model file
        self.__writeModel(model, metamodel, outputfiles)
        #/ 2.- writting the openModelica script file
        self.__writeRunner(metamodel, model, outputfiles)
        
        return None
    
    def __writeModel(self, model, metamodel, outputfiles):
    
        '''
        This method writes the openModelica model file.
        '''

        #/ 0.- Some initial variables necessary for the affectors module.
        option = 'openModelica'
        cellIndex = 0
        #/ 1.- writting the Modelica model file
        file = open(outputfiles.openModelicaModel, 'w')    
        file.write('//\n// generated by ByoDyn version %s\n//\n'%initiator.BYODYNVERSION)
        file.write('model %s\n' %model.systemName)
        n = []
        for variable in n:
            if model.nodes.count(variable) == 1:
                model.algebraicNodes[variable] = model.initialConditions.pop(model.nodes.index(variable))
                model.nodes.remove(variable)
        delayEquations = {}
        assignmentOfEvents = {}
        #/ writting pow function
        file.write('\tfunction pow\n\t\tinput Real x;\n\t\tinput Real y;\n\t\toutput Real z:=x^y;\n\tend pow;\n')
        #/ writting sbml defined functions
        for function in model.functions:
            file.write('\tfunction %s\n' %function.id)
            for argument in function.arguments:
                file.write('\t\tinput Real %s;\n' %argument)
            if len(re.findall('pi',function.output)) != 0:
                file.write('\t\tparameter Real pi = 3.14159265;\n')          
            squareRootDefinitions = re.findall('root\(2, [\w\[\]()/\+\-\*\s\d\.\^\,]*\)', function.output)
            if len(squareRootDefinitions) != 0:
                function.output = function.output.replace('root(2, ', 'sqrt(')
            file.write('\t\toutput Real result:=%s;\n' %function.output)
            file.write('\tend %s;\n' %function.id)
        for event in model.events:
            if event.delay != None:
                file.write('\tReal delay%s(start=%s);\n' %(event.id, str(float(metamodel.simulationTime)/float(metamodel.simulationTimeStep)*10)))
                file.write('\tparameter Real timeStep=%s;\n'%(metamodel.simulationTimeStep))          
        #/ 1.1.- writting the nodes and its initial conditions
        for i in range(len(model.initialConditions)):
            if model.nodes[i] in model.constantNodes.keys():
                file.write('\tparameter Real %s=%s;\n'%(model.nodes[i], model.initialConditions[i]))
            else:
                file.write('\tReal %s(start=%s);\n' %(model.nodes[i], model.initialConditions[i]))
        for node in model.algebraicNodes.keys():
            file.write('\tReal %s(start=%s);\n'%(node, model.algebraicNodes[node]))        
        #/ 1.2.- writting the parameters
        for parameter in model.nonConstantParameters:
            if parameter == 'flow': # Because flow is restricted word in Modelica language
                file.write('\tReal flo(start=%s);\n'%(model.nonConstantParameters[parameter]))
            else:
                file.write('\tReal %s(start=%s);\n'%(parameter, model.nonConstantParameters[parameter]))
        for parameter in model.parameters:
            if parameter == 'flow': # Because flow is restricted word in Modelica language
                file.write('\tparameter Real flo=%s;\n'%(model.parameters[parameter]))
            else:
                file.write('\tparameter Real %s=%s;\n'%(parameter, model.parameters[parameter]))
        for nonConstantCompartment in model.nonConstantCompartments.keys():
            file.write('\tReal %s(start=%s);\n'%(nonConstantCompartment, model.nonConstantCompartments[nonConstantCompartment]['size']))
        for compartment in model.compartments.keys():
            file.write('\tparameter Real %s=%s;\n'%(compartment, model.compartments[compartment]['size']))
        addedEquation = []
        #/ 1.3.- writting the equations
        file.write('equation\n')
        for i in range (model.xlength):
            for j in range (model.ywidth):
                for event in model.events:
                    #/ SBML specification: an event can only be triggered immediately after initial simulation time i.e., t > 0
                    #/ We add in the trigger of when clause a condition more in order to only fire the events for time > 0
                    if event.delay != None:
                        file.write('\twhen ((%s) and (time > 0)) then\n\t\treinit(delay%s,%s);\n\tend when;\n' %(event.trigger, event.id, event.delay))
                        file.write('\twhen (%s) then\n\t\treinit(%s,%s);\n' %('delay%s<timeStep' %event.id, 'delay%s' %event.id, str(float(metamodel.simulationTime)/float(metamodel.simulationTimeStep)*10)))
                        for variable in event.assignment.keys():
                                if model.nodes.count(variable) == 0:
                                    find = False
                                    for rule in model.rules:
                                        if variable == rule.variable:
                                            find = True
                                    if variable in addedEquation:
                                        find = True
                                    if find == True:
                                        file.write('\t\treinit(%s,%s);\n' %(variable, event.assignment[variable]))
                                    else:
                                        file.write('\t\t%s = %s;\n' %(variable, event.assignment[variable]))                                        
                                        addedEquation.append(variable)
                                else:
                                    file.write('\t\treinit(%s,%s);\n' %(variable, event.assignment[variable]))
                        file.write('\tend when;\n')
                        file.write('\tder(delay%s) = %s;\n' %(event.id, '- timeStep'))
                    else:
                        file.write('\twhen ((%s) and (time > 0)) then\n' %(event.trigger))                                            
                        for variable in event.assignment.keys():
                                if model.nodes.count(variable) == 0:
                                    find = False
                                    for rule in model.rules:
                                        if variable == rule.variable:
                                            find = True
                                    if variable in addedEquation:
                                        find = True
                                    if find == True:
                                        file.write('\t\treinit(%s,%s);\n' %(variable, event.assignment[variable]))
                                    else:
                                        file.write('\t\t%s = %s;\n' %(variable, event.assignment[variable]))                                        
                                        addedEquation.append(variable)
                                else:
                                    file.write('\t\treinit(%s,%s);\n' %(variable, event.assignment[variable]))
                        file.write('\tend when;\n')
                
                for node in model.nodes:
                    if model.constantNodes.keys().count(node) == 0:
                        file.write('\tder(%s) = ' %(node))
                        first = 0
                        for definition in model.topology.keys():
                            fieldsDefinition = definition.split('/')
                            if fieldsDefinition[0] == node:
                                exec "%s(model, file, option, cellIndex, definition, fieldsDefinition)"%fieldsDefinition[1]
                                first = 1
                        if first == 0:
                            file.write('0')
                        file.write(';\n')
                for rule in model.rules:
                    if rule.type == 'Rate':
                        file.write('\tder(%s) = ' %(rule.variable))
                        formulas.writeOpenModelicaFormula(rule.math, file)
                    if rule.type == 'Algebraic':                    
                        file.write('\t0 = ')
                        formulas.writeOpenModelicaFormula(rule.math, file)
                    if rule.type == 'Assignment':
                        file.write('\t%s = ' %rule.variable)
                        formulas.writeOpenModelicaFormula(rule.math, file)
                    file.write(';\n')
        file.write('end %s;\n' %model.systemName)
        file.close()

        return None

    def __writeRunner(self, metamodel, model, outputfiles):
    
        '''
	This method writes the openModelica options file.
	'''
        
        script = open(outputfiles.openModelicaInput, 'w')
        script.write('//\n// generated by ByoDyn version %s\n//\n'%initiator.BYODYNVERSION)
        script.write('echo(false);\n')
        script.write('loadFile("%s");\n' %outputfiles.openModelicaModel)
        script.write('simulate(%s, startTime=0.0,stopTime=%s, numberOfIntervals=%s);\n' %(model.systemName, metamodel.simulationTime, int(metamodel.simulationTime / metamodel.simulationTimeStep)))
        script.close()
    
        return None

    def callSolver(self, outputfiles):
    
        '''
        This method calls openModelica to simulate the model
        '''
	
	currentDirectory = os.getcwd()
        os.chdir(outputfiles.scratchdir)
        os.system('omc %s' %(outputfiles.openModelicaInput))
	os.chdir(currentDirectory)
        
        return None
    
    def createOutputs(self, model, outputfiles, metamodel):

        '''
        This method converts the format of the openModelica output file into a more adequate for ByoDyn.
        '''    
    
        variables = []
        for n in model.nodes:
            variables.append(n)
        for n in model.algebraicNodes:
            variables.append(n)
        for n in model.nonConstantParameters:
            variables.append(n)
        for n in model.nonConstantCompartments:
            variables.append(n)        
    
        results = {}
        node = None
        resultFile = open(outputfiles.openModelicaOutput, 'r')
        for line in resultFile:
            if line.startswith('DataSet') == True:
                line = line.rstrip("\r\n")
                if line.split()[1] == 'time' or line.split()[1] in variables:
                    node = line.split()[1]
                    results[node] = []
                else:
                    node = None
            elif re.match('[\d.]+,\s[\d.-]+', line) != None and node != None:
                results[node].append(line.split()[1])
        i = 0

        if len(results['time']) > len(results[variables[0]]):
            results['time'].__delitem__(len(results['time'])-1)
        
        for j in range(len(results['time'])):
            if results['time'][j-i] in results['time'][:(j-i)]:
                for r in results:
                    results[r].__delitem__(j-i)
                i += 1

        file = open(outputfiles.simulationResults, 'w')    
        file.write('#\n# generated by ByoDyn version %s\n#\n# t'%initiator.BYODYNVERSION)
        for n in variables:
            file.write('\t%s' %n)    
        for i in range(len(results['time'])):
            file.write('\n%s'%results['time'][i])
            for n in variables:
                if model.constantNodes.keys().count(n) == 0:    
                    file.write('\t%s' %results[n][i])
                else:
                    file.write('\t%s' %model.constantNodes[n])                
        file.write('\n')
        #/ in the case of csv output format
        if 'csv' in metamodel.optionalOutputFormat:
            file = open(outputfiles.simulationResultsCSV, 'w')    
	    file.write('#\n# generated by ByoDyn version %s\n#\n'%initiator.BYODYNVERSION)
            file.write('time') 
            for n in variables:
                file.write(',%s' %n)    
            for i in range(len(results['time'])):
                file.write('\n%s' %results['time'][i])
                for n in variables:
                    if model.constantNodes.keys().count(n) == 0:    
                        file.write(',%s' %results[n][i])
                    else:
                        file.write(',%s' %model.constantNodes[n])
            file.write('\n')
        
        return None
