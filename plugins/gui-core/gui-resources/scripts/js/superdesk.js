var superdesk = 
{
	/*!
	 * repository for templates
	 */
	tmplRepo: $('<div />'),
	/*!
	 * Loads template files via ajax and extracts the templates
	 * 
	 * @param string path 
	 * 	the url from which to load templates
	 * @param string selector 
	 * 	optional, selector to use to match templates in loaded file
	 * @returns $.Deferred
	 */
	getTmpl: function(path)
	{
		var tplSelector = typeof arguments[1] != 'undefined' ? arguments[2] : "script[type='text/x-jQuery-tmpl']", 
			dfd = new $.Deferred;
		$.ajax(path, {dataType: 'html'}).done(function(html)
		{ 
			var templates = [];
			$(html).each(function(i, elem){ if($(elem).is(tplSelector)) templates.push(elem); });
			superdesk.tmplRepo.append(templates);
			dfd.resolve(templates);
		});
		return dfd;
	},
	layouts: {},
	/*!
	 * load layout to superdesk object layouts
	 * @param string path 
	 * 	layout path
	 * @param string name 
	 * 	layout name
	 */
	loadLayout: function(path, name)
	{
		return $.ajax( superdesk.apiUrl+path, {dataType: 'html'})
			.done(function(data)
			{
				// need to wrap it in a <div /> tag for $ selector to work
				var layoutObject = $('<div>'+data+'</div>');
				if( typeof name == 'string')
					superdesk.layouts[name] = layoutObject;
				else
					name = layoutObject;
				
				return layoutObject;
			});
	},
	/*!
	 * cache repo
	 */
	cache: {actions: {}, scripts: {}},
	/*!
	 * @param string path 
	 * @returns $.Deferred()
	 */
	getActions: function(path)
	{
		var dfd = $.Deferred();
		if( !superdesk.cache.actions[path] )
		{
			new $.rest(superdesk.apiUrl + '/resources/GUI/Action?path='+path)
				.done(function(actions)
				{ 
					superdesk.cache.actions[path] = actions;
					dfd.resolve(actions);
				});
			return dfd;
		}
		return dfd.resolve(superdesk.cache.actions[path]);
	},
	/*!
	 * 
	 */
	navigation: 
	{
	    _repository: {},
	    _base: '',
	    _titlePrefix: '',
        bind: function(href, callback, title)
        {
            if(typeof callback !== 'function') return false;
            
            var History = window.History;
            this._repository[href] = callback;
            History.pushState({href: href}, title ? this._titlePrefix + title : null, this._base + href);
            return callback;
        },
        init: function(callback)
        {
            var History = window.History, 
                State = History.getState(),
                self = this;
            
            History.options.debug = true;
            this._base = History.getPageUrl().split('#')[0];
                
            History.Adapter.bind( window, 'statechange', function()
            {
                var State = History.getState();
                (self._repository[State.data.href])();
            });
                
            if( typeof callback === 'function' )
            {
                this._repository[''] = callback;
                History.pushState( {href: ''}, $(document).prop('title'), this._base );
                History.Adapter.trigger( window, 'statechange' );
            }
        }
	},
	/*!
	 * 
	 */
	presentation: function(script, layout, args)
	{
		var _setScript = function(value){ script = value; };
		this.setScript = function(value){ _setScript(value); return this; };
		this.getScript = function(){ return script; };
		
		var _setLayout = function(value){ layout = value; };
		this.setLayout = function(value){ _setLayout(value); return this; };
		this.getLayout = function(){ return layout; };
		
		var _setArgs = function(value){ args = value; };
		this.setArgs = function(value){ _setArgs(value); return this; };
		this.getArgs = function(){ return args; };
		
		var script = script,
			layout = layout || null,
			args = args || null,
			self = this,
			t$ = function(selector){ return $(selector, superdesk.tmplRepo); };
		
		/*!
		 * Loads and applies script to a layout object
		 * 
		 * @param string scriptPath 
		 * @param object layoutObject 
		 * @param object additional
		 * 	additional parameters to be passed
		 */
		this.run = function()
		{
			if(arguments[0]) _setScript(arguments[0]); // set script
			if(arguments[1]) _setLayout(arguments[1]); // set layout
			if(arguments[2]) _setArgs(arguments[2]); // set args
			
			var dfd = $.Deferred();
			dfd.done(function(scriptText)
			{
				// TODO additional security checking here
			    (new Function('$', 't$', 'layout', 'args', scriptText))
                    .call(self, $, t$, layout, args);
			});
			if( !superdesk.cache.scripts[script] )
			{
				$.ajax(superdesk.apiUrl + '/' + script, {dataType: 'text'})
					.done(function(data)
					{
						superdesk.cache.scripts[script] = data;
						dfd.resolve(data);
					});
				return dfd;
			}
			return dfd.resolve(superdesk.cache.scripts[script]);
		};
		
		this.direct = function(href, script, layout, args, title)
		{
		    if( typeof href === 'object' )
		    {
		        switch(true)
		        {
		            case typeof href.script !== 'undefined': script = href.script; 
                    case typeof href.layout !== 'undefined': layout = href.layout;
                    case typeof href.args !== 'undefined': args = href.args;
                    case typeof href.title !== 'undefined': title = href.title;
                    case typeof href.href !== 'undefined': href = href.href;
		        }
		    }
		    var self = this,
		        fnc = function(){ self.setScript(script).setLayout(layout).setArgs(args).run(); };
		        
		    if( typeof href === 'string' )
		    {
		        superdesk.navigation.bind( href, fnc, title );
		        return;
		    }
		    (fnc)();
		};
	}
};
superdesk.presentation.prototype = 
{
	view:
	{
		prefix: function(){ return superdesk.apiUrl+'/content/gui/superdesk/'; },
		load: function(template)
		{
			return superdesk.getTmpl( (typeof this.prefix == 'function' ? this.prefix() : this.prefix) + template);
		},
		render: function(selector, data)
		{
			if(typeof selector == 'string') var tmpl = $(selector, superdesk.tmplRepo);
			else var tmpl = selector;

			// TODO tpl
			var compiled = $($.tmpl(tmpl, data));

			console.log(compiled);
			
			return compiled;
		}
	},
	form:
	{
		add: function(html, nodeName)
		{
			if(!nodeName) return html;
			$(html).find('input, textarea, select').each(function()
			{
				var name = $(this).attr('name') || '';
				$(this).attr('name', name.replace(/^([^\[]+)/, nodeName+'[$1]'));
			});
			return $(html);
		}
	}
};
