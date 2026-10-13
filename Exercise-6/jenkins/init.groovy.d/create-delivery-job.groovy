// Create the pipeline job from the Jenkinsfile, the same as pasting it into
// New Item > Pipeline > Pipeline script in the Jenkins web UI
import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition

def name = 'delivery-monitoring-pipeline'
def jenkins = Jenkins.get()
def job = jenkins.getItem(name) ?: jenkins.createProject(WorkflowJob, name)
job.setDescription('ZAPPTTO delivery monitoring: build the metrics app and run Prometheus + Grafana')
job.setDefinition(new CpsFlowDefinition(new File('/project/Jenkinsfile').text, true))
job.save()
println "Created pipeline job: ${name}"
