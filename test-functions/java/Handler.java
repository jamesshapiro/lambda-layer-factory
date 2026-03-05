package layertest;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class Handler implements RequestHandler<Map<String, Object>, Map<String, Object>> {

    @Override
    public Map<String, Object> handleRequest(Map<String, Object> event, Context context) {
        Map<String, Object> results = new HashMap<>();

        @SuppressWarnings("unchecked")
        List<String> testClasses = (List<String>) event.getOrDefault("test_imports",
                List.of("com.google.common.collect.ImmutableList"));

        for (String className : testClasses) {
            try {
                Class<?> clazz = Class.forName(className);
                results.put(className, Map.of("status", "ok", "class", clazz.getName()));
            } catch (ClassNotFoundException e) {
                results.put(className, Map.of("status", "error", "message", e.getMessage()));
            }
        }

        Map<String, Object> response = new HashMap<>();
        response.put("statusCode", 200);
        response.put("body", results);
        return response;
    }
}
