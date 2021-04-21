jquery.flowchart
================

Javascript jQuery plugin that allows you to draw a flow chart. Take a look at the demo:
http://sebastien.drouyer.com/jquery.flowchart-demo/

Description
-----------

jquery.flowchart.js is an open source javascript jQuery ui plugin that allows you to draw and edit a flow chart.

Here are the main functionalities provided so far:
* Draw boxes (called operators) and connections between them.
* Methods are provided so that the end-user can edit the flow chart by adding / moving / removing operators, creating / removing connections between them.
* The developper can save / load the flowchart.
* Operators and links can be customized using CSS and the plugin parameters.
* Some methods allow you to add advanced functionalities, such as a panzoom view or adding operators using drag and drop. Take a look at the [advanced demo](http://sebastien.drouyer.com/jquery.flowchart-demo/#advanced).

Context
-------

This project is part of a bigger one, [UltIDE](https://github.com/ultide/ultide) which allows you to have a complete interface managing a flowchart and custom properties. Though it is still WIP, you are welcome to give it a try and contribute. A screenshot is shown below.

![UltIDE Screenshot](https://ultide.github.io/ultide-documentation/images/screenshot.png?version=2)

License
-------
jquery.flowchart.js is under [MIT license](https://github.com/sdrdis/jquery.flowchart/blob/master/MIT-LICENSE.txt).

Authors
-------
* [Sebastien Drouyer](http://sebastien.drouyer.com) - alias [@sdrdis](https://twitter.com/sdrdis) - for this jquery ui plugin

Contributors
------------
* Simone Gasparini - alias [@simmyg89](https://github.com/simmyg89) - for bug fixes and code formatting.
* Guijin Ding - alias [@dingguijin](https://github.com/dingguijin) - for bug fixes.
* M. Fatih Marabaoğlu - alias [@MFatihMAR](https://github.com/MFatihMAR) - for adding the uncontained parameter and improving the grid system.
* Peter Vavro - alias [@petervavro](https://github.com/petervavro) - for adding mouse events.
* Mike Branham - alias [@Mike-Branham](https://github.com/Mike-Branham) - for bug fixes in the demo page.
* [@zhangbg](https://github.com/zhangbg) - for compatibility with IE9, IE10 and IE11.
* [@elvaron](https://github.com/elvaron) - for bug fixes and adding the getLinksFrom and getLinksTo methods.
* Ziyi Wang - alias [@ziyiwang](https://github.com/ziyiwang) - for bug fixes.
* [@dogbull](https://github.com/dogbull) - for adding the getDataRef method.
* Yaroslav Zenin - alias [@yaroslav-zenin](https://github.com/yaroslav-zenin) - for big fixes.
* [@lflfm](https://github.com/lflfm) - for bug fixes and new demo page.
* [@neoera](https://github.com/neoera) - for adding multiple sub connector with array support.
* Dima Shemendiuk - alias [@dshemendiuk](https://github.com/dshemendiuk) - for adding vertical flowchart support and access to operators's body.
* Ernani Azevedo - alias [@ernaniaz](https://github.com/ernaniaz) - for adding the possibility to decide for each connector if there can be a single link and multiple links and for making the integration of features from the community much easier.

Documentation
-------------

### Demo:

http://sebastien.drouyer.com/jquery.flowchart-demo/

### Terminology:

![Terminology](http://sebastien.drouyer.com/jquery.flowchart-demo/images/terminology.png)

### Options:

* __canUserEditLinks (default: true):__ Can the user add links by clicking on connectors. Note that links can be removed during the process if `multipleLinksOnInput`of `multipleLinksOnOutput`are set to false.

* __canUserMoveOperators (default: true):__ Can the user move operators using drag and drop.

* __data (default: `{}`):__ Initialization data defining the flow chart operators and links between them.

  * __operators:__ Hash defining the operators in your flow chart. The keys define the operators ID and the value define each operator's information as follow:
    * __top (in px)__
    * __left (in px)__
    * __type__: (optional) The type of the operator. See `data.operatorTypes`.
    * __properties:__
      * __title__
      * __body__
      * __uncontained:__ (optional, default: `false`) If `true`, the operator can be moved outside the container.
      * __class:__ css classes added to the operator DOM object. If undefined, default value is the same as `defaultOperatorClass`.
      * __inputs:__ Hash defining the box's input connectors. The keys define the connectors ID and the values define each connector's information as follow:
        * __label__: Label of the connector. If the connector is __multiple__, '(:i)' is replaced by the subconnector ID.
        * __multipleLinks__: (optional) If `true`, allow multiple links to this connector.
        * __multiple__: (optional) If `true`, whenever a link is created on the connector, another connector (called subconnector) is created. See the [multiple connectors demo](http://sebastien.drouyer.com/jquery.flowchart-demo/#multiple).
      * __outputs:__ Hash defining the box's output connectors. Same structure as `inputs`.
      
  * __links:__ Hash defining the links between your operators in your flow chart. The keys define the link ID and the value define each link's information as follow:
    * __fromOperator:__ ID of the operator the link comes from.
    * __fromConnector:__ ID of the connector the link comes from.
    * __fromSubConnector:__ (optional) If it is a multiple connector, which subconnector is it.
    * __toOperator:__ ID of the operator the link goes to.
    * __toConnector:__ ID of the connector the link goes to.
    * __toSubConnector:__ (optional) If it is a multiple connector, which subconnector is it.
    * __color:__ Color of the link. If undefined, default value is the same as `defaultLinkColor`.
    
  * __operatorTypes:__ (optional) Hash allowing you to define common operator types in order to not repeat the properties key. Key define the operator's type ID and the value define the properties (same structure as `data.operators.properties`).

* __verticalConnection (default: false):__ Allows to build vertical-connected flowcharts. __WARNING:__ When using vertical connectors, avoid using multiple connectors, because it will break layout.

* __distanceFromArrow (default: 3):__ Distance between the output connector and the link.

* __defaultLinkColor (default: '#3366ff'):__ Default color of links.

* __defaultSelectedLinkColor (default: 'black'):__ Default color of links when selected.

* __defaultOperatorClass (default: 'flowchart-default-operator'):__ Default class of the operator DOM element. 

* __linkWidth (default: 11):__ Width of the links.

* __grid (default: 20):__ Grid of the operators when moved. If its value is set to 0, the grid is disabled.

* __multipleLinksOnInput (default: false):__ Allows multiple links on the same input connector.

* __multipleLinksOnOutput (default: false):__ Allows multiple links on the same output connector.

* __linkVerticalDecal (default: 0):__ Allows to vertical decal the links (in case you override the CSS and links are not aligned with their connectors anymore).

* __onOperatorSelect (default: function returning true):__ Callback method. Called when an operator is selected. It should return a boolean. Returning `false` cancels the selection. Parameters are:
  * __operatorId:__ ID of the operator.

* __onOperatorUnselect (default: function returning true):__ Callback method. Called when an operator is unselected. It should return a boolean. Returning `false` cancels the unselection.

* __onOperatorMouseOver (default: function returning true):__ Callback method. Called when the mouse pointer enters an operator. It should return a boolean. Returning `false` cancels the selection. Parameters are:
  * __operatorId:__ ID of the operator.

* __onOperatorMouseOut (default: function returning true):__ Callback method. Called when the mouse pointer leaves an operator. It should return a boolean. Returning `false` cancels the unselection.

* __onLinkSelect (default: function returning true):__ Callback method. Called when a link is selected. It should return a boolean. Returning `false` cancels the selection. Parameters are:
  * __linkId:__ ID of the link.

* __onLinkUnselect (default: function returning true):__ Callback method. Called when a link is unselected. It should return a boolean. Returning `false` cancels the unselection.

* __onOperatorCreate (default: function returning true):__ Callback method. Called when an operator is created. It should return a boolean. Returning `false` cancels the creation. Parameters are:
  * __operatorId:__ ID of the operator.
  * __operatorData:__ Data of the operator.
  * __fullElement:__ Hash containing DOM elements of the operator. It contains:
    * __operator:__ the DOM element of the whole operator.
    * __title:__ the DOM element of the operator's title.
    * __connectorArrows:__ the DOM element of the connectors' arrows.
    * __connectorSmallArrows:__ the DOM element of the connectors' small arrows.

* __onOperatorDelete (default: function returning true):__ Callback method. Called when an operator is deleted. It should return a boolean. Returning `false` cancels the deletion. Parameters are:
  * __operatorId:__ ID of the operator.

* __onLinkCreate (default: function returning true):__ Callback method. Called when a link is created. It should return a boolean. Returning `false` cancels the creation. Parameters are:
  * __linkId:__ ID of the link.
  * __linkData:__ Data of the link.

* __onLinkDelete (default: function returning true):__ Callback method. Called when a link is deleted. It should return a boolean. Returning `false` cancels the deletion. Parameters are:
  * __linkId:__ ID of the link.
  * __forced:__ The link deletion can not be cancelled since it happens during an operator deletion.

* __onOperatorMoved (default: function):__ Callback method. Called when an operator is moved. Parameters are:
  * __operatorId:__ ID of the operator.
  * __position:__ New position of the operator.
  
* __onAfterChange (default: function):__ Callback method. Called after changes have been done (operator creation for instance). Parameters are:
  * __changeType:__ What change did occur. Can be one of these strings:
    * operator_create
    * link_create
    * operator_delete
    * link_delete
    * operator_moved
    * operator_title_change
    * operator_body_change
    * operator_data_change
    * link_change_main_color

### Events

All callbacks (options with a name that begins with "on") have their event counterpart. For instance, the callback
`onOperatorSelect(operatorId)` has an equivalent event that can be handled using
`$(flowchartEl).on('operatorSelect', function(el, operatorId, returnHash) { /* your code here */ })`, where
`flowchartEl` is the DOM element of the flowchart.

If `onOperatorSelect` doesn't return `false`, the event `operatorSelect` is triggered, and the final return value
will be `returnHash['result']`. The behaviour is similar for all callbacks.

### Functions
#### Operators:
* __createOperator(operatorId, operatorData):__
  * __Parameters:__
    * __operatorId__
    * __operatorData:__ Same as in `data.operators`.
    
* __addOperator(operatorData):__
  * __Description:__ Same as `createOperator`, but automatically sets the operator's ID.
  * __Parameters:__
    * __operatorData:__ Same as in `data.operators`.
  * __Return:__ The operator's ID.

* __deleteOperator(operatorId):__
  * __Parameters:__
    * __operatorId__

* __getSelectedOperatorId():__
  * __Return:__ The operator ID if one is selected, `null` otherwise.

* __selectOperator(operatorId):__
  * __Parameters:__
    * __operatorId__

* __unselectOperator():__

* __addClassOperator(operatorId, className):__
  * __Parameters:__
    * __operatorId__
    * __className__: Class name to add.

* __removeClassOperator(operatorId, className):__
  * __Parameters:__
    * __operatorId__
    * __className__: Class name to remove.

* __removeClassOperators(className):__
  * __Parameters:__
    * __className__: Remove class name from all operators.

* __setOperatorTitle(operatorId, title):__
  * __Parameters:__
    * __operatorId__
    * __title:__ The operator's new title to be set.

* __setOperatorBody(operatorId, body):__
  * __Parameters:__
    * __operatorId__
    * __body:__ The operator's new body html to be set.

* __getOperatorTitle(operatorId):__
  * __Parameters:__
    * __operatorId__
  * __Return:__ The operator's title.

* __getOperatorBody(operatorId):__
  * __Parameters:__
    * __operatorId__
  * __Return:__ The operator's body.

* __doesOperatorExists(operatorId):__
  * __Description:__ This method checks whether or not an operator with id equal to `operatorId` exists.
  * __Parameters:__
    * __operatorId__

* __setOperatorData(operatorId, operatorData):__
  * __Description:__ This method replaces the operator's data. Note that if new connectors are renamed / removed, the flowchart can remove links.
  * __Parameters:__
    * __operatorId__
    * __operatorData__: Same as in `data.operators`.

* __getOperatorData(operatorId):__
  * __Parameters:__
    * __operatorId__
  * __Return:__ The operator's data. Same as in `data.operators`.

* __getConnectorPosition(operatorId, connectorId):__ 
  * __Parameters:__
    * __operatorId__
    * __connectorId__
  * __Return:__ The connector's position relative to the container.

* __getOperatorCompleteData(operatorData):__
  * __Parameters:__
    * __operatorData:__ The operator's data. Same as in `data.operators`.
  * __Return:__ Completes the operator's data with default values if some keys are not defined (like `class` for instance).

* __getOperatorElement(operatorData):__
  * __Parameters:__
    * __operatorData:__ The operator's data. Same as in `data.operators`.
  * __Return:__ The operator's DOM element (jquery). The element is not added in the container. It can be used to preview the operator or showing it during a drag and drop operation.

* __getLinksFrom(operatorId):__
  * __Parameters:__
    * __operatorId:__ The operator's Id.
  * __Return:__ Array with all links from the provided operator.

* __getLinksTo(operatorId):__
  * __Parameters:__
    * __operatorId:__ The operator's Id.
  * __Return:__ Array with all links to the provided operator.

* __getOperatorFullProperties(operatorData):__
  * __Parameters:__
    * __operatorData:__ The operator's data. Same as in `data.operators`.
  * __Return:__ If not operator type is defined, the `property` key. Otherwise, the `property` key extended with the operator's type properties.
  

#### Links:
* __createLink(linkId, linkData):__
  * __Parameters:__
    * __linkId__
    * __linkData:__ Same as in `data.links`.

* __addLink(linkData):__
  * __Description:__ Same as `createLinks`, but automatically sets the link's ID.
  * __Parameters:__
    * __linkData:__ Same as in `data.links`.
  * __Return:__ The link's ID.

* __deleteLink(linkId):__
  * __Parameters:__
    * __linkId__

* __getSelectedLinkId():__ 
  * __Return:__ The link ID if one is selected, `null` otherwise.
  
* __selectLink(linkId):__
  * __Parameters:__
    * __linkId__

* __unselectLink()__

* __setLinkMainColor(linkId, color):__
  * __Parameters:__
    * __linkId__
    * __color__

* __getLinkMainColor(linkId):__
  * __Parameters:__
    * __linkId__
  * __Returns:__ The link's color.

* __colorizeLink(linkId, color):__
  * __Description:__ Sets the link a temporary color contrary to `setLinkMainColor`. It can be used to temporarly highlight a link for instance.
  * __Parameters:__
    * __linkId__
    * __color__

* __uncolorizeLink(linkId):__
  * __Description:__ Sets the link color back to its main color.
  * __Parameters:__
    * __linkId__

* __redrawLinksLayer():__
  * __Description:__ Redraws all the links.
  

  
#### Misc:
* __getData():__
  * __Return:__ The flow chart's data. Same structure as the `data` option.

* __setData(data):__
  * __Parameters:__
    * __data:__ Same structure as the `data` option.

* __getDataRef():__
  * __Return:__ The internal system flow chart's data.

* __setPositionRatio(positionRatio):__
  * __Parameters:__
    * __positionRatio:__ The ratio between the mouse position and the position of the DOM elements. Used when drag and dropping the operators. You should use it if you zoom the container. See the [advanced demo](http://sebastien.drouyer.com/jquery.flowchart-demo/#advanced).

* __getPositionRatio():__
  * __Return:__ The position ratio.

* __deleteSelected():__
  * __Description:__ Deletes the link or operator selected.
