package com.jcqrslib.jcqrs.cqrs;

import org.springframework.beans.BeansException;
import org.springframework.beans.factory.config.ConfigurableListableBeanFactory;
import org.springframework.beans.factory.support.BeanDefinitionRegistry;
import org.springframework.beans.factory.support.BeanDefinitionRegistryPostProcessor;
import org.springframework.context.annotation.Configuration;

/**
 * Scans all beans that implement IRequestHandler and creates an alias for each one, 
 * transforming the handler's class name into a more predictable name. 
 * For example, (getClienteByIdRequestHandler).
 * 
 * Escanea todos los beans que implementan IRequestHandler y crea un alias para cada uno, 
 * transformando el nombre de clase del handler a un nombre más predecible. 
 * Por ejemplo, (getClienteByIdRequestHandler).
 */
@Configuration
public class RequestHandlerAliasConfig implements BeanDefinitionRegistryPostProcessor {

    /**
     * Register in programatic mode beans.
     * 
     * Registra beans de forma programática
     */
    @Override
    public void postProcessBeanDefinitionRegistry(BeanDefinitionRegistry registry) {
        // Not Implemented
    }

    /**
     * Whole register of the beans definitions.
     * 
     * Registra todos los beans definidos.
     */
    @Override
    public void postProcessBeanFactory(ConfigurableListableBeanFactory beanFactory) throws BeansException {
        String[] beanNames = beanFactory.getBeanNamesForType(IRequestHandler.class);

        for (String beanName : beanNames) {
            Class<?> type = beanFactory.getType(beanName);

            if (type != null) {
                String aliasName = buildAliasName(type.getSimpleName());
                if (!beanFactory.containsBean(aliasName)) {
                    ((BeanDefinitionRegistry) beanFactory).registerAlias(beanName, aliasName);
                    System.out.println("🔗 Alias registrado: " + aliasName + " → " + beanName);
                }
            }
        }
    }

    /**
     * Calls a helper method to generate the alias name from the class name.
     * 
     * Llama a un método auxiliar para generar el nombre del alias a partir del nombre de la clase.
     * @param className
     * @return
     */
    private String buildAliasName(String className) {
        // Manipulation of interoperative classes convention.
        if (className.endsWith("Handler")) {
            return Character.toLowerCase(className.charAt(0)) +
                    className.substring(1).replace("Handler", "RequestHandler");
        }
        return className;
    }
}
