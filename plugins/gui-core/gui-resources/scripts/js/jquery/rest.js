$(function()
{
	var dfdManager = 
	{
		add: function(parentDfd, childDfd)
		{
			childDfd.children = [];
			if(typeof parentDfd.children == 'undefined') parentDfd.children = [];
			parentDfd.children.push(childDfd);
		},
		stop: function(dfd)
		{
			if(typeof dfd.children != 'undefined')
				for(var i in dfd.children)
					dfdManager.stop(dfd.children[i]);
			dfd.reject();
		}
	};
	
	function chainable(fn, name)
	{
		this.deferred = $.Deferred();
		//this.deferred.progress(function(){ console.log('progress '+this.name+' with', arguments) })
		this.fn = fn;
		this.name = name;
	};
	chainable.prototype.promise = function()
	{
		return this.deferred.promise();
	};
	chainable.prototype.invoke = function()
	{
		this.fn.apply(this, arguments)
		return this;
	};
	
	/*!
	 * construct
	 */
	function resource()
	{
		var self = this;
		
		//this.uniqueId = (new Date).getTime();
		
		this._ = '';
		
		this.getData = [];
		this.lastAdded = {};
		this.job = [];
		this.initXFrom = false;
		
		this.requestOptions = 
		{
			dataType: 'json',
			type: 'get',
			headers: { 'Accept' : 'text/json' } 
		};
		
		var extractListData = function(data)
		{
			var ret = data;
			if( !Array.isArray(data) ) for( i in data ) 
			{
				if( Array.isArray(data[i]) ) 
					ret = data[i];
				break;
			}
			return ret;
		}
		this.extractListData = extractListData;
		
		if( typeof arguments[0] == 'string' )
		{
			this.request({url : arguments[0] });
			this.initData = new chainable( function()
			{
				if( typeof this.request != 'undefined' )
					self.request(this.request);
				return self.doRequest()
					.pipe(function(data)
					{
						var ret = extractListData(data);
						self.initData.fn = function(){ this.deferred.resolve(ret); return ret; };
						return ret;
					})
					.then(this.deferred.resolve, this.deferred.reject);
			}, 'initData from ajax');
		}
		else
		{
			var ret = extractListData(arguments[0]);
			this.initData = new chainable(function()
			{ 
				this.deferred.resolve(ret); return ret; 
			}, 'initData with data');
		}
		
		this.lastAdded = this.initData;
		
		this.fromData = new chainable(function(data){ this.deferred.resolve(data); }, 'fromInit');
		var fromData = this.fromData,
			self = this;
		
		fromData.promise().always(function(){ self.initXFrom = false; })
		self.initXFrom = true;
		$.when(this.initData).then(function()
		{
			fromData.invoke.apply(fromData, arguments);
		}, fromData.deferred.reject );
		
		if(arguments[1]) this.name = arguments[1];
		
	};

	resource.prototype.chainable = chainable;
	
	/*!
	 * get item from the already existing list
	 */
	resource.prototype.from = function(key)
	{
		var self = this,
			args = arguments;
		
		this.fromData = new chainable( function(list)
		{
			var found = false;
			for( var item in list )
			{
				if( typeof key != 'object' && item != key ) continue;
				found = list[item];
				// for each key check if exists and is the value	
				for( keyName in key )
					if(!(keyName in list[item]) || list[item][keyName] != key[keyName])
					{
						found = false;
						break;
					}
				if( found ) break;
			}
			
			if( !found || typeof found.href == 'undefined' ) return this.deferred.reject();
			var fromUrl = found.href;
				
			if( args.length > 1 ) 
			{
				if(typeof args[1] == 'function')
					fromUrl = args[1](found);
				if(typeof args[1] == 'object')
					self.request(args[1]);
				if(typeof args[2] == 'object')
					self.request(args[2]);
			}
			
			if( typeof this.request != 'undefined' )
				self.request(this.request);
			
			return self
				.doRequest(fromUrl)
				.pipe(function(data)
				{ 
					self.fromData.fn = function()
					{ 
						this.deferred.resolve(data); 
						return data; 
					};
					return data;
				})
				.then(this.deferred.resolve, this.deferred.reject);
			
		}, "from "+key);
		
		var fromData = this.fromData;
		this.lastAdded = fromData;

		if(!self.initXFrom)
		{
			self.iniXFrom = true;
			$.when(this.initData).then(function(){ fromData.invoke.apply(fromData, arguments); }, fromData.deferred.reject );
		}
		
		if( typeof this.insideJob != 'undefined' )
			this.insideJob.push(fromData);
		
		return this;
	};
	
	/*!
	 * register an operation to obtain a key value from an object node
	 * obtained by the last operation either from or construct
	 */
	resource.prototype.get = function(key)
	{
		var self = this;
		var args = arguments;
		var getData = new chainable( function(data) 
		{
			var node;
			if( !Array.isArray(data) ) 
				if( Object.keys(data).length == 1 )
				{
					for( var i in data )
						if( key in data[i] )
							node = data[i][key]
				}
				else if(typeof data[key] != 'undefined') node = data[key];

			if(typeof node == 'undefined') 
			{
				this.deferred.reject();
				return false;
			}

			// assume that we only have a href property provided and we need to follow it to get the entity
			if(typeof node.href == 'string' && Object.keys(node).length == 1)
			{
				var dfd = this.deferred;
				if(typeof args[1] != 'undefined' )
					self.request(args[1]);
				
				if( typeof this.request != 'undefined' )
					self.request(this.request);
				
				var ajax = self.doRequest(node.href)
					//.pipe(function(data){ return data; })
					.then(this.deferred.resolve, this.deferred.reject);
				return ajax;
			}
			// assume we have all/the filtered properties
			else
				return this.deferred.resolve(node);
		}, "get "+key);
		
		this.getData.push(getData);
		this.lastAdded = getData;
		
		$.when(this.fromData).then(function(){ getData.invoke.apply(getData, arguments); }, getData.deferred.reject );
		
		if( typeof this.insideJob != 'undefined' )
			this.insideJob.push(getData);
		
		return this;
	};
	
	/*!
	 * execute operations and optionally execute a callback
	 */
	resource.prototype.done = function()
	{
		if( !this.getData.length )
		{
			var getInit = new chainable(function(data)
			{
				this.deferred.resolve(data);
			}, 'getInit');
			getInit.isInit = true;
			this.getData = [getInit];
			$.when(this.fromData).then(function(){ getInit.invoke.apply(getInit, arguments); }, getInit.deferred.reject );
		}
				
		var self = this,
			name = arguments[1];
		
		if( typeof arguments[0] == 'function' )
		{
			var callback = arguments[0],
				failCallback = $.noop;
			
			if(typeof arguments[1] == 'function')
				failCallback = arguments[1];
			
			$.when.apply($, this.getData).then(function()
			{
				var args = $.makeArray(arguments);
				if( typeof self.spawned != 'undefined' )
					args = args.concat(self.spawned);
				var result = callback.apply(self, args);
			}, 
			function()
			{
				failCallback.apply(self, arguments);
			})
			.always(function() // we need to reset at least initData for future chains..
			{
				self.initData = new chainable(self.initData.fn, 'reset');
				self.fromData = new chainable(self.fromData.fn, 'reset');
				//self.fromData = new chainable(self.fromData.fn);
				self.initXFrom = true
				$.when(self.initData).then(function()
				{ 
					self.fromData.invoke.apply(self.fromData, arguments); 
				}, self.fromData.deferred.reject );
			});	
		}
		
		var trigger = $.Deferred();
		trigger.resolve();
		var initData = this.initData;
		$.when(trigger).then(function(){ initData.invoke.apply( initData, arguments ); });
		self.getData = [];
		return this;
	};
	
	resource.prototype.resetJob = function()
	{
		if(typeof this.job == 'undefined') return this;
		for(var i in this.job)
			this.job[i].deferred.reject();
		this.job = [];
		return this;
	};
	
	resource.prototype.registerToJob = function(job)
	{
		this.insideJob = job;
		return this;
	};
	
	/*!
	 * execute this callback regardless of fail or done get operations
	 */
	resource.prototype.always = function(callback)
	{
		var self = this;
		var dfd = $.Deferred();
		$.when(dfd).then(function(data)
		{ 
			if(typeof callback == 'function')
				callback.apply(self, data);
		});
		var progress = this.getData.length;
		var args = [];
		$(this.getData).each(function(i, fn)
		{
			fn.promise().always(function()
			{
				progress--;
				if(arguments.length > 1) // if more than 1 argument put them in an array
					args.splice(i, 0, arguments);
				else // else just the single one 
					args.splice(i, 0, arguments[0]);
				if(!progress) 
					dfd.resolve(args);
			});	
		})
		return this;
	};
	
	/*!
	 * spawn a new resource rom the last get method called
	 */
	resource.prototype.spawn = function()
	{
		var self = this;
		//if(this.getData.length)
		//	$.when(this.getData[this.getData.length-1]).pipe(function(data)
			$.when(this.lastAdded).pipe(function(data)
			{
				self.spawned = new resource(data, 'spawned');
				// TODO add backreference or not?
				return data;
			});
		return this;
	};
	
	/*!
	 * make the request
	 * @param string url
	 */
	resource.prototype.doRequest = function()
	{
		if(typeof arguments[0] == 'string') this.request({url : arguments[0]});
		var ajax = $.ajax(this.requestOptions);
		delete this.requestOptions.headers['X-Filter'];
		return ajax;
	};
	
	/*!
	 * extend request options
	 */
	resource.prototype.request = function(options)
	{
		$.extend(true, this.requestOptions, options);
		return this;
	};
	
	resource.prototype.xfilter = function(value)
	{
		this.lastAdded.request = { headers: { 'X-Filter' : value } };
		return this;
	};
	
	$.extend($, {rest : resource});
});