"""Simplified tracking API for logging ALL visits."""
from datetime import datetime
from typing import Optional
import json
from fastapi import APIRouter, Request, Response, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import structlog

from app.database import get_db
from app.services.tracking import TrackingService
from app.utils.rate_limiting import RateLimiter

logger = structlog.get_logger()

router = APIRouter(prefix="/track", tags=["tracking"])
tracking_service = TrackingService()
rate_limiter = RateLimiter()

# Pre-minified JS tracker (minified with terser, ~12KB)
_JS_TEMPLATE_MINIFIED = '!function(){try{var t=window.CrawlDoctor||(window.CrawlDoctor={});if(t._loaded)return;function e(t){try{return window[t]}catch(t){return null}}t._loaded=!0;var n=e("sessionStorage"),r=e("localStorage");function a(t,e){try{return t?t.getItem(e):null}catch(t){return null}}function i(t,e,n){try{t&&t.setItem(e,n)}catch(t){}}a(n,"cd_page_view_sent")||i(n,"cd_page_view_sent","1");var o=__TID__,c=(__PAGE_URL__,__VISIT_ID__),l=function(){var t=document.currentScript;if(!t){var e=document.getElementsByTagName("script");t=e[e.length-1]}return t&&t.src||""}(),u=function(){try{return new URL(l).origin}catch(t){return location.protocol+"//"+location.host}}();var s=function(t){try{var e=(t||location.hostname).split(".");if(e.length<=2)return e.join(".");var n=e.slice(-2).join("."),r=e.slice(-3).join(".");return["co.uk","org.uk","ac.uk","gov.uk","com.au","net.au","co.nz"].indexOf(r)>=0?r:n}catch(t){return location.hostname}}(location.hostname),d="cd_cid_"+(o||s),h=null;try{var f=new URLSearchParams(window.location.search);if(f.has("cd_cid")){h=f.get("cd_cid"),f.delete("cd_cid");var v=f.toString(),p=window.location.pathname+(v?"?"+v:"")+window.location.hash;window.history.replaceState({},document.title,p)}}catch(q){}try{if(h||(h=a(r,d)),!h){var m=document.cookie.match(new RegExp("(^| )cd_cid=([^;]+)"));m&&(h=m[2])}h||(h=([1e7]+-1e3+-4e3+-8e3+-1e11).toString().replace(/[018]/g,function(t){return(t^crypto.getRandomValues(new Uint8Array(1))[0]&15>>t/4).toString(16)})),i(r,d,h);try{var g=new Date;g.setFullYear(g.getFullYear()+1),document.cookie="cd_cid="+h+"; path=/; domain="+s+"; expires="+g.toUTCString()+"; samesite=Lax"}catch(J){}}catch(Y){}function y(){var t={};try{t.title=document.title;for(var e=document.getElementsByTagName("meta"),n=0;n<e.length;n++){var r=e[n],a=r.getAttribute("name")||r.getAttribute("property");a&&(a.indexOf("description")>=0||a.indexOf("og:title")>=0||a.indexOf("keywords")>=0)&&(t[a]=r.getAttribute("content"))}}catch(t){}return t}document.addEventListener("mousedown",function(t){try{var e=t.target.closest("a");if(!e||!e.href)return;var n=new URL(e.href);-1!==n.hostname.indexOf(s)&&n.origin!==window.location.origin&&(n.searchParams.set("cd_cid",h),e.href=n.toString())}catch(t){}},!0);var w=null;function _(){if(w)return w;var t={};try{t.timezone=Intl.DateTimeFormat().resolvedOptions().timeZone}catch(t){}try{t.language=navigator.language||navigator.userLanguage}catch(t){}try{t.screen_resolution=window.screen.width+"x"+window.screen.height}catch(t){}try{t.viewport_size=window.innerWidth+"x"+window.innerHeight}catch(t){}try{navigator.deviceMemory&&(t.device_memory=navigator.deviceMemory+"GB")}catch(t){}try{navigator.connection&&(t.connection_type=navigator.connection.effectiveType||navigator.connection.type)}catch(t){}return w=t,t}var b=!1;function k(t,e){if(!b){b=!0;try{var n={event_type:t,page_url:window.location.href,referrer:document.referrer||null,data:e||{},visit_id:c,tid:o,cid:h,client_side_data:_(),page_metadata:y()},r=u+"/track/event?tid="+encodeURIComponent(o||""),a=JSON.stringify(n);if(navigator.sendBeacon)try{if(navigator.sendBeacon(r,a))return void(b=!1)}catch(t){}if(window.fetch)try{fetch(r,{method:"POST",body:a,headers:{"Content-Type":"text/plain"},keepalive:!0}).catch(function(t){}).finally(function(){b=!1})}catch(t){b=!1}else b=!1}catch(t){b=!1}}}var L="cd_pv_"+location.pathname+location.search;a(n,L)||(i(n,L,Date.now()),k("page_view",{viewport:{w:window.innerWidth,h:window.innerHeight},tracking_method:"javascript",cid:h})),document.addEventListener("click",function(t){try{var e=t.target,n=e&&e.closest?e.closest(\'a,button,[role="button"]\'):null;if(!n)return;k("click",{href:("A"===n.tagName?n.href:null)||null,text:n.innerText||n.getAttribute("aria-label")||n.name||n.id||null,id:n.id||null,class:n.className||null,tracking_method:"javascript"})}catch(t){}},{passive:!0});var E=null;window.addEventListener("scroll",function(){E||(E=setTimeout(function(){E=null;var t=window.scrollY||document.documentElement.scrollTop||0,e=document.documentElement.scrollHeight||0,n=window.innerHeight||0;k("scroll",{y:t,percent:e?Math.round((t+n)/e*100):0,tracking_method:"javascript"})},1e3))},{passive:!0}),document.addEventListener("visibilitychange",function(){k("visibility",{state:document.visibilityState,tracking_method:"javascript"})});var x=Date.now(),S=Date.now();function T(){var t=Date.now();return{time_on_page_ms:t-x,idle_time_ms:t-S,engaged:t-S<3e4,tracking_method:"javascript"}}function C(){S=Date.now()}document.addEventListener("click",C,{passive:!0}),document.addEventListener("scroll",C,{passive:!0}),document.addEventListener("keypress",C,{passive:!0}),setInterval(function(){"visible"===document.visibilityState&&k("heartbeat",T())},3e4),window.addEventListener("beforeunload",function(){try{var t=performance&&performance.getEntriesByType?performance.getEntriesByType("navigation")[0]:null,e=T();e.type=t&&t.type||"unknown",k("navigate",e)}catch(t){}});var A=location.href;function O(t){try{var e=location.href;e!==A&&(k("navigation",{type:t,from:A,to:e,tracking_method:"javascript"}),A=e)}catch(t){}}try{var j=history.pushState;history.pushState=function(){j.apply(history,arguments),O("pushState")};var N=history.replaceState;history.replaceState=function(){N.apply(history,arguments),O("replaceState")},window.addEventListener("popstate",function(){O("popstate")}),window.addEventListener("hashchange",function(){O("hashchange")})}catch(W){}function R(t,e,n,r){var a=t||"",i=function(t,e,n){var r=(e||"").toLowerCase();if("password"===(n||"").toLowerCase())return!0;for(var a=["password","pass","pwd","ssn","social","credit","card","cc","cvc","cvv","otp","token","secret","api_key","apikey","recaptcha","cvn","card_number","cvv2"],i=0;i<a.length;i++)if(r.indexOf(a[i])>=0)return!0;return!1}(0,n,r);if(i)return{value:null,masked:!0,length:a.length};var o=(""+a).trim();if(o.length>100&&/^[A-Za-z0-9+\\/=]{100,}$/.test(o))return{value:null,masked:!1,length:o.length,rejected:!0};if(0===o.indexOf("eyJ")&&3===o.split(".").length)return{value:null,masked:!1,length:o.length,rejected:!0};var c=o.replace(/[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F-\\x9F]/g,"");if(c.length>0){var l=c.match(/[a-zA-Z0-9\\s@._\\-+(),:;!?\'"]/g);if((l?l.length:0)/c.length<.3)return{value:null,masked:!1,length:c.length,rejected:!0}}if(c.length>0&&!/[a-zA-Z0-9]/.test(c))return{value:null,masked:!1,length:c.length,rejected:!0};var u=1e3;return{value:c.length>u?c.slice(0,u):c,masked:!1,length:c.length,truncated:c.length>u}}function U(t,e){try{if(!t)return!0;if(t.getAttribute&&"true"===t.getAttribute("aria-hidden"))return!0;var n=(e||"").toLowerCase();if("hidden"===n||"password"===n||"submit"===n||"button"===n||"reset"===n)return!0}catch(t){}return!1}var P={};function D(t){try{if(!t)return;var e=(t.getAttribute("type")||t.tagName||"").toLowerCase();if(U(t,e))return;var n=t.name||t.id||t.getAttribute("placeholder")||t.getAttribute("aria-label")||"unnamed",r="checkbox"===e||"radio"===e?t.checked?"1":"0":(t.value||"").trim();if(!r||r===P[n])return;P[n]=r;var a=R(r,0,n,e);if(null===a.value)return;k("form_input",{field_name:n,field_type:e,field_value:a.value,tracking_method:"javascript"})}catch(t){}}function I(t){try{if(!t)return;var e=Date.now();if(t._cd_last_submit_ts&&e-t._cd_last_submit_ts<1e3)return;t._cd_last_submit_ts=e;var n=t.id||null,r=t.getAttribute("name")||null,a=t.getAttribute("action")||null,i=(t.getAttribute("method")||"GET").toUpperCase(),o=function(t){var e=t.querySelectorAll("input,textarea,select"),n=0,r={};return e.forEach(function(t){var e=(t.getAttribute("type")||"").toLowerCase();if(!U(t,e)){var a=t.name||t.id||"field_"+Math.random().toString(36).substr(2,5),i="checkbox"===e||"radio"===e?t.checked?"1":"0":(t.value||"").trim();if(i){var o=R(i,0,a,e);null!==o.value&&(n+=1,r[a]=o.value)}}}),{filled:n,values:r}}(t);k("form_submit",{id:n,name:r,action:a,method:i,filled_fields:o.filled,form_values:o.values,tracking_method:"javascript"})}catch(t){}}document.addEventListener("blur",function(t){var e=t.target;!e||"INPUT"!==e.tagName&&"TEXTAREA"!==e.tagName&&"SELECT"!==e.tagName||D(e)},!0),document.addEventListener("change",function(t){var e=t.target;!e||"INPUT"!==e.tagName&&"TEXTAREA"!==e.tagName&&"SELECT"!==e.tagName||D(e)},!0),document.addEventListener("submit",function(t){try{I(t.target)}catch(t){}},!0),document.addEventListener("click",function(t){try{var e=t.target&&t.target.closest?t.target.closest("button, input"):null;if(!e)return;if("submit"!==(e.getAttribute("type")||"").toLowerCase())return;var n=e.form||(e.closest?e.closest("form"):null);if(!n)return;if(n.checkValidity&&!n.checkValidity())return;setTimeout(function(){I(n)},0)}catch(t){}},!0);var B=[{pattern:/^https:\\/\\/app\\.getmaxim\\.ai\\/api\\//,pathContains:"/sign-up",method:"POST"},{pattern:/^https:\\/\\/(www\\.)?getmaxim\\.ai\\/api\\//,pathContains:["/bifrost/book-a-demo","/bifrost/enterprise"],method:"POST"},{pattern:/^https:\\/\\/api\\.cal\\.com\\//,pathContains:["/demo","/schedule","/bifrost/book-a-demo","/bifrost/enterprise"],method:"POST"}];function M(t,e){try{for(var n=new URL(t,window.location.href).href,r=(e||window.location.pathname).toLowerCase(),a=0;a<B.length;a++){var i=B[a];if(i.pattern.test(n)){if(i.pathContains){for(var o=Array.isArray(i.pathContains)?i.pathContains:[i.pathContains],c=!1,l=0;l<o.length;l++)if(r.indexOf(o[l].toLowerCase())>=0){c=!0;break}if(!c)continue}return!0}}}catch(t){}return!1}function F(t){try{for(var e=new URL(t,window.location.href),n=e.hostname.toLowerCase(),r=e.pathname.toLowerCase(),a=["posthog","segment","analytics","google-analytics","googletagmanager","amplitude","mixpanel","hotjar","fullstory","heap","intercom","pendo","logrocket","ghost","ph.getmaxim","reo.dev","api.reo.dev","twitter.com","ads.linkedin","cloudflareinsights"],i=0;i<a.length;i++)if(n.indexOf(a[i])>=0)return!0;var o=["/analytics/","/tracking/","/telemetry/","/flags/","/decide/","/ghost/event","/adsct"];for(i=0;i<o.length;i++)if(r.indexOf(o[i])>=0)return!0}catch(t){}return!1}function z(t,e){var n={},r=0;e=e||"";try{for(var a in t){if(r>=50)break;if(t.hasOwnProperty(a)){for(var i=t[a],o=e?e+"."+a:a,c=["phc_","distinct_id","anonymous","token","uuid","session_id","timestamp","version","api_key","device_id"],l=!1,u=0;u<c.length;u++)if(o.toLowerCase().indexOf(c[u])>=0){l=!0;break}if(!l)if("string"==typeof i){var s=R(i,0,o,null);null!==s.value&&(n[o]=s.value,r++)}else if("number"==typeof i||"boolean"==typeof i)n[o]=i,r++;else if("object"==typeof i&&null!==i&&e.split(".").length<3){var d=z(i,o);for(var h in d){if(r>=50)break;n[h]=d[h],r++}}}}}catch(t){}return n}function H(t,e,n){try{if(!M(t,window.location.pathname))return;if(F(t))return;var r=function(t){try{if(!t)return{};if("string"==typeof t){try{return z(JSON.parse(t))}catch(t){}try{var e=new URLSearchParams(t),n={};return e.forEach(function(t,e){n[e]=t}),z(n)}catch(t){}}else if("object"==typeof t)return z(t)}catch(t){}return{}}(n),a=Object.keys(r).length;if(0===a)return;k("form_submit",{id:null,name:null,action:t,method:e,filled_fields:a,form_values:r,tracking_method:"javascript",source:"network_intercept"})}catch(t){}}if(window.fetch){var G=window.fetch;window.fetch=function(){var t=arguments,e=t[0],n=t[1]||{},r=(n.method||"GET").toUpperCase();try{if("POST"===r&&M(e,window.location.pathname)&&!F(e))try{H(e,r,n.body)}catch(t){}}catch(t){}return G.apply(this,t)}}if(window.XMLHttpRequest){var V=window.XMLHttpRequest,X=V.prototype.open,Z=V.prototype.send;V.prototype.open=function(t,e){return this._cd_method=t,this._cd_url=e,X.apply(this,arguments)},V.prototype.send=function(t){try{var e=(this._cd_method||"").toUpperCase(),n=this._cd_url;"POST"===e&&n&&M(n,window.location.pathname)&&(F(n)||H(n,e,t))}catch(t){}return Z.apply(this,arguments)}}try{new MutationObserver(function(t){t.forEach(function(t){t.addedNodes.forEach(function(t){1===t.nodeType&&"FORM"===t.tagName&&t.addEventListener("submit",function(t){I(t.target)},!0)})})}).observe(document.body,{childList:!0,subtree:!0})}catch($){}}catch(K){}}();'

def _get_client_ip(request: Request) -> str:
    """Extract client IP considering reverse proxy headers."""
    try:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # XFF may contain multiple IPs, take the first
            ip = xff.split(",")[0].strip()
            if ip:
                return ip
        xri = request.headers.get("x-real-ip")
        if xri:
            return xri.strip()
        fwd = request.headers.get("forwarded")
        if fwd and "for=" in fwd:
            # e.g., for=1.2.3.4;proto=https;by=...
            try:
                part = [p for p in fwd.split(";") if p.strip().lower().startswith("for=")][0]
                ip = part.split("=", 1)[1].strip().strip('"')
                # Remove optional port
                if ip.startswith("[") and "]" in ip:
                    ip = ip[1:ip.index("]")]
                else:
                    ip = ip.split(":")[0]
                if ip:
                    return ip
            except Exception:
                pass
    except Exception:
        pass
    return request.client.host

@router.get("/js")
async def track_js(
    request: Request,
    tid: Optional[str] = Query(None, description="Tracking ID"),
    page: Optional[str] = Query(None, description="Page identifier")
):
    """JavaScript tracking endpoint with client-side instrumentation and single-fire guard."""
    try:
        client_ip = _get_client_ip(request)
        if not await rate_limiter.is_allowed(client_ip, "js_track"):
            return Response(content="/* Rate limited */", media_type="application/javascript")
        
        referrer = request.headers.get("referer")
        page_url = page or referrer
        
        logger.debug("JavaScript tracker served", tid=tid)
        
        js_content = (
            _JS_TEMPLATE_MINIFIED
            .replace("__TID__", json.dumps(tid or ""))
            .replace("__PAGE_URL__", json.dumps(page_url or ""))
            .replace("__VISIT_ID__", "null")
        )
        
        return Response(
            content=js_content,
            media_type="application/javascript",
            headers={
                "Cache-Control": "public, max-age=300",  # Cache for 5 minutes (faster updates)
                "Access-Control-Allow-Origin": "*",
                "X-Content-Version": "2.1"  # Version marker for debugging
            }
        )
        
    except Exception as e:
        logger.error("JavaScript tracking failed", error=str(e))
        return Response(
            content="/* CrawlDoctor tracking error */",
            media_type="application/javascript"
        )


@router.get("/json")
async def track_json(
    tid: Optional[str] = Query(None, description="Tracking ID")
):
    """Lightweight JSON tracking endpoint for legacy/prefetch requests."""
    return Response(
        content="{}",
        media_type="application/json",
        headers={
            "Cache-Control": "public, max-age=300",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.post("/event")
async def track_event(
    request: Request,
    db: Session = Depends(get_db),
    tid: Optional[str] = Query(None, description="Tracking ID")
):
    """Record granular client-side events (click, scroll, navigation, etc.)."""
    try:
        client_ip = _get_client_ip(request)
        if not await rate_limiter.is_allowed(client_ip, "event_track"):
            return Response(content="Rate limited", status_code=429)

        # Support both JSON and text/plain bodies
        try:
            payload = await request.json()
        except Exception:
            try:
                body = await request.body()
                payload = json.loads(body.decode('utf-8') or '{}')
            except Exception:
                payload = {}
        event_type = payload.get("event_type")
        page_url = payload.get("page_url")
        referrer = payload.get("referrer")
        data = payload.get("data")
        visit_id = payload.get("visit_id")
        client_id = payload.get("cid")
        client_side_data = payload.get("client_side_data")

        if not event_type:
            # Ignore empty/malformed payloads to reduce noise and error logs
            return Response(status_code=204)

        user_agent = request.headers.get("user-agent", "")

        result = await tracking_service.track_event(
            db=db,
            ip_address=client_ip,
            user_agent=user_agent,
            event_type=event_type,
            page_url=page_url,
            referrer=referrer,
            data=data,
            visit_id=visit_id,
            tracking_id=tid,
            client_id=client_id,
            client_side_data=client_side_data,
        )

        return {"status": "tracked", "event_id": result.get("event_id"), "queued": result.get("queued")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Event tracking failed", error=str(e))
        return {"status": "error", "message": str(e)}


@router.get("/status")
async def tracking_status():
    """Health check endpoint for tracking service."""
    return {
        "status": "healthy",
        "service": "tracking",
        "timestamp": datetime.now().isoformat()
    }
